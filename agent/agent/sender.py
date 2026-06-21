import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timezone

import requests

from agent.buffer import clear_queue, dequeue_all, enqueue

logger = logging.getLogger(__name__)

AGENT_VERSION = "2.0.0"
SIGNING_ENABLED = False  # Set True when server has AGENT_REQUEST_SIGNING=true


def _sign(api_key: str, timestamp: str, nonce: str, body: bytes) -> str:
    message = f"{timestamp}.{nonce}.".encode() + body
    return hmac.new(api_key.encode(), message, hashlib.sha256).hexdigest()


class Sender:
    def __init__(self, server_url: str, api_key: str, *, signing: bool = False) -> None:
        self.base = server_url.rstrip("/")
        self.api_key = api_key
        self.signing = signing or SIGNING_ENABLED
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Content-Type": "application/json", "X-Agent-Version": AGENT_VERSION})

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
        try:
            r = self.session.post(f"{self.base}{path}", data=body, headers=headers, timeout=15)
            if r.status_code == 401:
                logger.error("Invalid API key or signature rejected")
                return False
            r.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.warning("Request failed: %s", e)
            if buffer_kind:
                enqueue(buffer_kind, data)
            return False

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

    @staticmethod
    def register(server_url: str, enrollment_token: str, hostname: str, ip_address: str, os_info: str) -> str:
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
