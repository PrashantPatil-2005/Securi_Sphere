"""Agent HTTP sender with HMAC signing, exponential backoff, and offline buffer.

The agent sends events/metrics/heartbeats to the backend over HTTPS.
If the server is unreachable, data is buffered in SQLite and retried
with exponential backoff.

Signing (optional): Each request includes a timestamp, nonce, and HMAC-SHA256
signature computed over the request body. This prevents replay attacks —
the server tracks seen nonces and rejects duplicates.
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timezone

import requests

from agent.buffer import clear_queue, dequeue_all, enqueue, queue_size

logger = logging.getLogger(__name__)

AGENT_VERSION = "2.0.0"
SIGNING_ENABLED = False

# Retry configuration
INITIAL_BACKOFF_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 60.0
BACKOFF_MULTIPLIER = 2.0
MAX_RETRIES_BEFORE_BUFFER = 3


def _sign(api_key: str, timestamp: str, nonce: str, body: bytes) -> str:
    """HMAC-SHA256 signature: sign(timestamp.nonce.body).

    Server validates by recomputing and checking nonce hasn't been seen.
    This prevents replay attacks — even if an attacker captures a valid
    request, they can't resend it (nonce is single-use, timestamp expires).
    """
    message = f"{timestamp}.{nonce}.".encode() + body
    return hmac.new(api_key.encode(), message, hashlib.sha256).hexdigest()


class Sender:
    """HTTP sender with automatic retry and offline buffering.

    Flow:
    1. Try to POST to server
    2. On success: reset backoff, return True
    3. On failure: increment backoff, buffer to SQLite, return False
    4. On next loop iteration: flush buffer first, then send new data
    """

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
        # Exponential backoff state
        self._consecutive_failures = 0
        self._current_backoff = INITIAL_BACKOFF_SECONDS
        self._last_attempt = 0.0

    def _get_backoff(self) -> float:
        """Calculate current backoff with exponential increase + jitter."""
        base = min(
            INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER ** self._consecutive_failures),
            MAX_BACKOFF_SECONDS,
        )
        # Add small jitter (0-20%) to prevent thundering herd
        jitter = base * 0.2 * secrets.randbelow(100) / 100
        return base + jitter

    def _post(self, path: str, data: dict, buffer_kind: str | None = None) -> bool:
        body = json.dumps(data, separators=(",", ":"), default=str).encode()
        headers = {}
        if self.signing:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            nonce = secrets.token_hex(16)
            headers = {
                "X-Agent-Timestamp": ts,
                "X-Agent-Nonce": nonce,
                "X-Agent-Signature": _sign(self.api_key, ts, nonce, body),
            }

        # Respect backoff — don't hammer a down server
        now = time.time()
        wait = self._get_backoff() - (now - self._last_attempt)
        if wait > 0 and self._consecutive_failures > 0:
            logger.info("Backing off %.1fs (attempt %d failed)", wait, self._consecutive_failures)
            time.sleep(wait)

        self._last_attempt = time.time()

        try:
            r = self.session.post(f"{self.base}{path}", data=body, headers=headers, timeout=15)
            if r.status_code == 401:
                logger.error("Invalid API key or signature rejected")
                self._consecutive_failures += 1
                return False
            if r.status_code == 429:
                # Rate limited — back off aggressively
                retry_after = int(r.headers.get("Retry-After", 30))
                logger.warning("Rate limited, backing off %ds", retry_after)
                time.sleep(retry_after)
                self._consecutive_failures += 1
                if buffer_kind:
                    enqueue(buffer_kind, data)
                return False
            r.raise_for_status()
            # Success — reset backoff
            self._consecutive_failures = 0
            self._current_backoff = INITIAL_BACKOFF_SECONDS
            return True
        except requests.RequestException as e:
            self._consecutive_failures += 1
            logger.warning(
                "Request failed (%d consecutive): %s",
                self._consecutive_failures, e,
            )
            if buffer_kind and self._consecutive_failures >= MAX_RETRIES_BEFORE_BUFFER:
                logger.info("Buffering to SQLite after %d failures", self._consecutive_failures)
                enqueue(buffer_kind, data)
            return False

    @property
    def is_online(self) -> bool:
        """Whether the agent considers itself connected to the server."""
        return self._consecutive_failures == 0

    def heartbeat(self, payload: dict | None = None) -> bool:
        return self._post("/api/v1/agent/heartbeat", payload or {})

    def send_events(self, events: list[dict]) -> bool:
        if not events:
            return True
        return self._post("/api/v1/agent/events", {"events": events}, "events")

    def send_metrics(self, metrics: list[dict]) -> bool:
        if not metrics:
            return True
        return self._post("/api/v1/agent/metrics", {"metrics": metrics}, "metrics")

    def flush_buffer(self) -> None:
        """Drain the offline SQLite buffer and replay to server.

        This is called at the start of each main loop iteration.
        If the server is still down, buffered items stay in SQLite.
        """
        buffered = queue_size()
        if buffered > 0:
            logger.info("Flushing %d buffered items", buffered)

        items = dequeue_all()
        if not items:
            return

        events_batch = []
        metrics_batch = []
        for kind, payload in items:
            if kind == "events":
                events_batch.extend(payload.get("events", [payload]))
            elif kind == "metrics":
                metrics_batch.extend(payload.get("metrics", [payload]))

        ok = True
        if events_batch:
            ok = self.send_events(events_batch) and ok
        if metrics_batch:
            ok = self.send_metrics(metrics_batch) and ok

        if ok:
            clear_queue()
            logger.info("Buffer flushed successfully (%d events, %d metrics)", len(events_batch), len(metrics_batch))
        else:
            logger.warning("Buffer flush partially failed — items remain in SQLite")

    @staticmethod
    def register(
        server_url: str,
        enrollment_token: str,
        hostname: str,
        ip_address: str,
        os_info: str,
    ) -> str:
        """One-time enrollment: exchange token for API key."""
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
