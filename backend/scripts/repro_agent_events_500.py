"""Reproduce POST /api/v1/agent/events against the running backend. Prints status only."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
for env_path in (ROOT / "backend" / ".env", ROOT / ".env"):
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

BASE = os.environ.get("REPRO_BASE_URL", "http://127.0.0.1:8000")
EMAIL = os.environ.get("REPRO_EMAIL", "admin@test.local")
PASSWORD = os.environ.get("DEV_USER_PASSWORD") or os.environ.get("REPRO_PASSWORD", "")


def v3_event(event_type: str, severity: str = "medium") -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "event_type": event_type,
        "severity": severity,
        "description": f"Agent v3.0.0 test: {event_type}",
        "source": "auth.log",
        "raw_log": f"Sep 6 12:00:00 kali sshd[1]: Failed password for root from 10.0.0.8 port 22 ssh2",
        "timestamp": ts,
    }


def main() -> int:
    if not PASSWORD:
        print("DEV_USER_PASSWORD missing")
        return 2

    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        health = client.get("/health/live")
        print(f"health/live {health.status_code} {health.text[:200]}")

        login = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        print(f"login {login.status_code}")
        if login.status_code != 200:
            print(login.text[:500])
            return 1

        host_res = client.post("/api/v1/hosts", json={"name": "repro-v3-events"})
        print(f"create host {host_res.status_code} {host_res.text[:300]}")
        if host_res.status_code != 200:
            return 1
        host_id = host_res.json()["id"]

        token_res = client.post(f"/api/v1/hosts/{host_id}/enrollment-token")
        print(f"enrollment-token {token_res.status_code}")
        if token_res.status_code != 200:
            print(token_res.text[:500])
            return 1
        token = token_res.json()["token"]

        reg = client.post(
            "/api/v1/agent/register",
            json={
                "enrollment_token": token,
                "hostname": "kali-repro",
                "ip_address": "10.0.0.50",
                "os_info": "Kali GNU/Linux",
            },
        )
        print(f"register {reg.status_code}")
        if reg.status_code != 200:
            print(reg.text[:800])
            return 1
        api_key = reg.json()["api_key"]
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

        hb = client.post(
            "/api/v1/agent/heartbeat",
            headers=headers,
            content=json.dumps(
                {"agent_version": "3.0.0", "agent_hash": "a" * 64},
                separators=(",", ":"),
            ).encode(),
        )
        print(f"heartbeat {hb.status_code} {hb.text[:300]}")

        events = [
            v3_event("ssh_login_failure"),
            v3_event("ssh_login_success", "low"),
            v3_event("sudo_usage", "low"),
            v3_event("service_failure", "high"),
            v3_event("service_start", "info"),
        ]
        body = json.dumps({"events": events}, separators=(",", ":"), default=str).encode()
        ev = client.post("/api/v1/agent/events", headers=headers, content=body)
        print(f"events mixed {ev.status_code} {ev.text[:1500]}")

        batch = [v3_event("ssh_login_failure") for _ in range(43)]
        body43 = json.dumps({"events": batch}, separators=(",", ":"), default=str).encode()
        ev43 = client.post("/api/v1/agent/events", headers=headers, content=body43)
        print(f"events 43 {ev43.status_code} {ev43.text[:1500]}")

        metrics_body = json.dumps(
            {
                "metrics": [
                    {
                        "cpu_percent": 12.5,
                        "memory_percent": 40.0,
                        "disk_percent": 55.0,
                        "network_in": 100,
                        "network_out": 200,
                        "load_average": [0.1, 0.2, 0.3],
                        "uptime_seconds": 1000,
                        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    }
                ]
            },
            separators=(",", ":"),
        ).encode()
        met = client.post("/api/v1/agent/metrics", headers=headers, content=metrics_body)
        print(f"metrics {met.status_code} {met.text[:800]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
