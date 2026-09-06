"""Agent HTTP sender with HMAC signing, exponential backoff, and offline buffer.

The agent sends events/metrics/heartbeats to the backend over HTTPS.
If the server is unreachable, individual events are buffered in SQLite
and retried with exponential backoff.

Signing (optional): Each request includes a timestamp, nonce, and HMAC-SHA256
signature computed over the request body. This prevents replay attacks —
the server tracks seen nonces and rejects duplicates.
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone

import requests

from agent.buffer import (
    dequeue_all,
    queue_size,
    remove_by_ids,
    purge_stale,
    STALE_ITEM_MAX_AGE_HOURS,
    _agent_rss_mb,
    _buffer_size_mb,
)

logger = logging.getLogger(__name__)

AGENT_VERSION = "3.0.0"
SIGNING_ENABLED = False

INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0
BACKOFF_MULTIPLIER = 2.0
MAX_RETRIES_BEFORE_BUFFER = 2
MAX_CONSECUTIVE_FAILURES = 50

MAX_SEND_BATCH_SIZE = 50
MAX_FLUSH_BATCH_SIZE = 200


def _sign(api_key: str, timestamp: str, nonce: str, body: bytes) -> str:
    message = f"{timestamp}.{nonce}.".encode() + body
    return hmac.new(api_key.encode(), message, hashlib.sha256).hexdigest()


class Sender:
    def __init__(self, server_url: str, api_key: str, *, signing: bool = False) -> None:
        self.base = server_url.rstrip("/")
        self.api_key = api_key
        self.signing = signing or SIGNING_ENABLED
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "X-Agent-Version": AGENT_VERSION,
        })
        self._consecutive_failures = 0
        self._current_backoff = INITIAL_BACKOFF_SECONDS
        self._last_attempt = 0.0
        self._backoff_event = threading.Event()
        self._auth_failed = False
        self._last_failure_log_time: float = 0.0
        self._failure_log_suppressed = False

    def _get_backoff(self) -> float:
        base = min(
            INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER ** self._consecutive_failures),
            MAX_BACKOFF_SECONDS,
        )
        jitter = base * 0.2 * secrets.randbelow(100) / 100
        return base + jitter

    def _interruptible_sleep(self, seconds: float) -> None:
        self._backoff_event.clear()
        self._backoff_event.wait(timeout=seconds)

    def abort_backoff(self) -> None:
        self._backoff_event.set()

    def _post(self, path: str, data: dict) -> bool:
        body = json.dumps(data, separators=(",", ":"), default=str).encode()
        body_bytes = len(body)
        headers = {}
        if self.signing:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            nonce = secrets.token_hex(16)
            headers = {
                "X-Agent-Timestamp": ts,
                "X-Agent-Nonce": nonce,
                "X-Agent-Signature": _sign(self.api_key, ts, nonce, body),
            }

        now = time.time()
        wait = self._get_backoff() - (now - self._last_attempt)
        if wait > 0 and self._consecutive_failures > 0:
            logger.info("Backing off %.1fs (attempt %d failed)", wait, self._consecutive_failures)
            self._interruptible_sleep(wait)

        self._last_attempt = time.time()

        try:
            r = self.session.post(f"{self.base}{path}", data=body, headers=headers, timeout=15)
            if r.status_code == 401:
                if not self._auth_failed:
                    logger.error("Credentials permanently rejected — agent authentication failed")
                self._auth_failed = True
                self._consecutive_failures = min(self._consecutive_failures + 1, MAX_CONSECUTIVE_FAILURES)
                return False
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 30))
                logger.warning("Rate limited, backing off %ds", retry_after)
                self._interruptible_sleep(retry_after)
                self._consecutive_failures = min(self._consecutive_failures + 1, MAX_CONSECUTIVE_FAILURES)
                return False
            r.raise_for_status()
            self._consecutive_failures = 0
            self._current_backoff = INITIAL_BACKOFF_SECONDS
            self._auth_failed = False
            self._failure_log_suppressed = False
            return True
        except requests.RequestException as e:
            self._consecutive_failures = min(self._consecutive_failures + 1, MAX_CONSECUTIVE_FAILURES)
            now = time.time()
            if now - self._last_failure_log_time > 60:
                logger.warning(
                    "Request failed (%d consecutive): %s",
                    self._consecutive_failures, e,
                )
                self._last_failure_log_time = now
                self._failure_log_suppressed = False
            elif not self._failure_log_suppressed:
                logger.warning(
                    "Request failed (%d consecutive) — suppressing further messages for 60s",
                    self._consecutive_failures,
                )
                self._failure_log_suppressed = True
            return False

    def close(self) -> None:
        self.session.close()

    @property
    def is_online(self) -> bool:
        return self._consecutive_failures == 0

    @property
    def is_auth_failed(self) -> bool:
        return self._auth_failed

    def heartbeat(self, payload: dict | None = None) -> bool:
        return self._post("/api/v1/agent/heartbeat", payload or {})

    def send_events(self, events: list[dict]) -> bool:
        if not events:
            return True
        for start in range(0, len(events), MAX_SEND_BATCH_SIZE):
            chunk = events[start : start + MAX_SEND_BATCH_SIZE]
            if not self._post("/api/v1/agent/events", {"events": chunk}):
                return False
        return True

    def send_metrics(self, metrics: list[dict]) -> bool:
        if not metrics:
            return True
        for start in range(0, len(metrics), MAX_SEND_BATCH_SIZE):
            chunk = metrics[start : start + MAX_SEND_BATCH_SIZE]
            if not self._post("/api/v1/agent/metrics", {"metrics": chunk}):
                return False
        return True

    def flush_buffer(self) -> None:
        purge_stale(STALE_ITEM_MAX_AGE_HOURS)

        buffered = queue_size()
        if buffered > 0:
            rss = _agent_rss_mb()
            db_mb = _buffer_size_mb()
            logger.info(
                "Buffer flush: %d items, db=%.1fMB, rss=%.0fMB",
                buffered, db_mb, rss,
            )

        items = dequeue_all()
        if not items:
            return

        sent_ids: list[int] = []
        total_events = 0

        for batch_start in range(0, len(items), MAX_FLUSH_BATCH_SIZE):
            batch = items[batch_start:batch_start + MAX_FLUSH_BATCH_SIZE]
            events_batch: list[dict] = []
            event_ids: list[int] = []
            metrics_batch: list[dict] = []
            metric_ids: list[int] = []

            for item_id, kind, payload in batch:
                if not isinstance(payload, dict):
                    continue
                if kind == "metric" or (
                    kind == "event"
                    and "event_type" not in payload
                    and ("cpu_percent" in payload or "recorded_at" in payload)
                ):
                    metrics_batch.append(payload)
                    metric_ids.append(item_id)
                elif kind == "event":
                    events_batch.append(payload)
                    event_ids.append(item_id)

            if events_batch:
                largest_event = max(len(json.dumps(e, default=str).encode()) for e in events_batch)
                if self.send_events(events_batch):
                    sent_ids.extend(event_ids)
                    total_events += len(events_batch)
                    logger.info(
                        "Flush chunk sent: %d events, largest=%d bytes",
                        len(events_batch), largest_event,
                    )
                else:
                    rss = _agent_rss_mb()
                    logger.warning(
                        "Flush chunk failed: %d events, largest=%d bytes, rss=%.0fMB — will retry",
                        len(events_batch), largest_event, rss,
                    )

            if metrics_batch:
                if self.send_metrics(metrics_batch):
                    sent_ids.extend(metric_ids)
                    logger.info("Flush chunk sent: %d metrics", len(metrics_batch))
                else:
                    logger.warning("Flush chunk failed: %d metrics — will retry", len(metrics_batch))

        if sent_ids:
            remove_by_ids(sent_ids)
            logger.info(
                "Buffer flushed: %d/%d items sent (%d events)",
                len(sent_ids), len(items), total_events,
            )
        if len(sent_ids) < len(items):
            remaining = len(items) - len(sent_ids)
            logger.warning("Buffer flush partial — %d items remain", remaining)

    @staticmethod
    def register(
        server_url: str,
        enrollment_token: str,
        hostname: str,
        ip_address: str,
        os_info: str,
    ) -> str:
        r = requests.post(
            f"{server_url.rstrip('/')}/api/v1/agent/register",
            json={
                "enrollment_token": enrollment_token,
                "hostname": hostname,
                "ip_address": ip_address,
                "os_info": os_info,
            },
            timeout=15,
        )
        r.raise_for_status()
        return r.json()["api_key"]
