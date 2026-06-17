import logging
import time

import psutil
import requests

from agent.buffer import clear_queue, dequeue_all, enqueue

logger = logging.getLogger(__name__)


class Sender:
    def __init__(self, server_url: str, api_key: str) -> None:
        self.base = server_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Content-Type": "application/json"})

    def _post(self, path: str, data: dict, buffer_kind: str | None = None) -> bool:
        try:
            r = self.session.post(f"{self.base}{path}", json=data, timeout=15)
            if r.status_code == 401:
                logger.error("Invalid API key")
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
