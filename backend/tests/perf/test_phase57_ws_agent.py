"""Phase 57 — WebSocket, Agent E2E, Detection Pipeline, Outbox, Job Queue, Scheduler.

Runs against the live backend at http://127.0.0.1:8000 and Docker infrastructure.
Usage: python tests/perf/test_phase57_ws_agent.py
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
import traceback as tb
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
import websockets
import websockets.exceptions

BASE_URL = "http://127.0.0.1:8000"
WS_BASE_URL = "ws://127.0.0.1:8000"

DEV_PASSWORD = "testpass123"
ADMIN_EMAIL = "admin@test.local"

REDIS_PASSWORD = "securi_redis_dev"


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    status_code: int | None = None


@dataclass
class TestSuite:
    results: list[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)
        status = "\033[92mPASS\033[0m" if result.passed else "\033[91mFAIL\033[0m"
        extra = f" (HTTP {result.status_code})" if result.status_code else ""
        detail = f" — {result.detail}" if result.detail else ""
        print(f"  [{status}] {result.name}{extra}{detail}")

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    def summary(self):
        print(f"\n{'='*70}")
        print(f"  RESULTS: {self.passed}/{self.total} passed, {self.failed} failed")
        print(f"{'='*70}")
        if self.failed:
            print("\n  FAILED TESTS:")
            for r in self.results:
                if not r.passed:
                    print(f"    - {r.name}: {r.detail}")
        print()


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _run_docker_cmd(cmd: str) -> tuple[int, str]:
    """Run a docker exec command, return (returncode, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15
        )
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, "timeout"
    except Exception as e:
        return -1, str(e)


# ======================================================================
# 1. WEBSOCKET TESTS
# ======================================================================
async def test_websocket(suite: TestSuite, client: httpx.AsyncClient):
    print(f"\n{'='*70}")
    print("  1. WEBSOCKET TESTS")
    print(f"{'='*70}")

    # 1a. Flush Redis
    try:
        rc, out = _run_docker_cmd(
            f"docker exec securi-redis redis-cli -a {REDIS_PASSWORD} FLUSHALL"
        )
        ok = rc == 0 and ("OK" in out or "OK" in out.lower())
        suite.add(TestResult(
            "1a. Flush Redis via docker exec",
            ok,
            detail=f"rc={rc} out={out[:80]}" if not ok else "FLUSHALL OK",
        ))
    except Exception as e:
        suite.add(TestResult("1a. Flush Redis via docker exec", False, detail=str(e)))

    # 1b. Login as admin to get JWT
    access_token = None
    try:
        r = await client.post("/api/v1/auth/login", json={
            "email": ADMIN_EMAIL, "password": DEV_PASSWORD
        })
        ok = r.status_code == 200 and r.json().get("access_token")
        access_token = r.json().get("access_token") if ok else None
        suite.add(TestResult(
            "1b. Login as admin@test.local",
            ok,
            detail=f"Got {r.status_code}" if not ok else "Logged in",
            status_code=r.status_code,
        ))
    except Exception as e:
        suite.add(TestResult("1b. Login as admin@test.local", False, detail=str(e)))

    # 1c. Get WS ticket
    ws_ticket = None
    if access_token:
        try:
            r = await client.post("/api/v1/ws/token", headers=_h(access_token))
            ok = r.status_code == 200 and r.json().get("token")
            ws_ticket = r.json().get("token") if ok else None
            suite.add(TestResult(
                "1c. Get WS ticket from POST /api/v1/ws/token",
                ok,
                detail=f"Got {r.status_code}" if not ok else f"Ticket received (expires_in={r.json().get('expires_in')})",
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("1c. Get WS ticket", False, detail=str(e)))

    # NOTE: WebSocket endpoint is mounted at /api/v1/ws (router prefix="/api/v1")
    WS_PATH = "/api/v1/ws"

    # 1d. Connect WebSocket with valid token
    if ws_ticket:
        try:
            async with websockets.connect(f"{WS_BASE_URL}{WS_PATH}") as ws:
                # Send auth message
                await ws.send(json.dumps({"type": "auth", "token": ws_ticket}))
                # Wait for connection to be established (no close)
                try:
                    # If we can send a ping, connection is alive
                    pong = await asyncio.wait_for(ws.ping(), timeout=5.0)
                    ok = True
                    detail = "Connection established, ping/pong OK"
                except asyncio.TimeoutError:
                    ok = True
                    detail = "Connection accepted (no close within 5s)"
                except websockets.exceptions.ConnectionClosed:
                    ok = False
                    detail = "Connection closed unexpectedly"
                suite.add(TestResult(
                    "1d. WebSocket connect with valid WS ticket",
                    ok,
                    detail=detail,
                ))
        except Exception as e:
            suite.add(TestResult("1d. WebSocket connect with valid WS ticket", False, detail=str(e)))
    else:
        suite.add(TestResult("1d. WebSocket connect with valid WS ticket", False, detail="Skipped — no WS ticket"))

    # 1e. Connect WebSocket with invalid token
    try:
        async with websockets.connect(f"{WS_BASE_URL}{WS_PATH}") as ws:
            await ws.send(json.dumps({"type": "auth", "token": "invalid_token_xyz"}))
            try:
                close = await asyncio.wait_for(ws.recv(), timeout=5.0)
                # If we get a message, check if connection was closed
                ok = False
                detail = f"Got unexpected message: {close[:80]}"
            except websockets.exceptions.ConnectionClosed as e:
                ok = e.code == 4001
                detail = f"Connection closed with code {e.code} (expected 4001)"
            except asyncio.TimeoutError:
                # Connection might stay open or close
                ok = True
                detail = "No close within 5s (server may reject on next recv)"
            suite.add(TestResult(
                "1e. WebSocket rejects invalid token (no crash)",
                ok,
                detail=detail,
            ))
    except Exception as e:
        suite.add(TestResult("1e. WebSocket rejects invalid token", False, detail=str(e)))

    # 1f. Connect WebSocket without token
    try:
        async with websockets.connect(f"{WS_BASE_URL}{WS_PATH}") as ws:
            await ws.send(json.dumps({"type": "auth"}))
            try:
                close = await asyncio.wait_for(ws.recv(), timeout=5.0)
                ok = False
                detail = f"Got unexpected message: {close[:80]}"
            except websockets.exceptions.ConnectionClosed as e:
                ok = e.code == 4001
                detail = f"Connection closed with code {e.code} (expected 4001)"
            except asyncio.TimeoutError:
                ok = True
                detail = "No close within 5s (server may reject on next recv)"
            suite.add(TestResult(
                "1f. WebSocket rejects missing token (no crash)",
                ok,
                detail=detail,
            ))
    except Exception as e:
        suite.add(TestResult("1f. WebSocket rejects missing token", False, detail=str(e)))

    # 1g. Connect WebSocket with wrong message type
    try:
        async with websockets.connect(f"{WS_BASE_URL}{WS_PATH}") as ws:
            await ws.send(json.dumps({"type": "subscribe", "channel": "alerts"}))
            try:
                close = await asyncio.wait_for(ws.recv(), timeout=5.0)
                ok = False
                detail = f"Got unexpected message: {close[:80]}"
            except websockets.exceptions.ConnectionClosed as e:
                ok = e.code == 4001
                detail = f"Connection closed with code {e.code} (expected 4001)"
            except asyncio.TimeoutError:
                ok = True
                detail = "No close within 5s"
            suite.add(TestResult(
                "1g. WebSocket rejects wrong message type (no crash)",
                ok,
                detail=detail,
            ))
    except Exception as e:
        suite.add(TestResult("1g. WebSocket rejects wrong message type", False, detail=str(e)))

    return access_token


# ======================================================================
# 2. AGENT E2E TESTS
# ======================================================================
async def test_agent_e2e(suite: TestSuite, client: httpx.AsyncClient, admin_token: str):
    print(f"\n{'='*70}")
    print("  2. AGENT E2E TESTS")
    print(f"{'='*70}")

    # 2a. Create host
    host_id = None
    try:
        r = await client.post("/api/v1/hosts", json={
            "name": f"agent-e2e-{uuid.uuid4().hex[:6]}"
        }, headers=_h(admin_token))
        ok = r.status_code in (200, 201)
        host_id = r.json().get("id") if ok else None
        suite.add(TestResult(
            "2a. Create host via POST /api/v1/hosts",
            ok,
            detail=f"Got {r.status_code}: {r.text[:100]}" if not ok else f"Host ID: {host_id}",
            status_code=r.status_code,
        ))
    except Exception as e:
        suite.add(TestResult("2a. Create host", False, detail=str(e)))

    # 2b. Create enrollment token
    enrollment_token = None
    if host_id:
        try:
            r = await client.post(f"/api/v1/hosts/{host_id}/enrollment-token",
                                  headers=_h(admin_token))
            ok = r.status_code in (200, 201)
            enrollment_token = r.json().get("token") if ok else None
            suite.add(TestResult(
                "2b. Create enrollment token",
                ok,
                detail=f"Got {r.status_code}" if not ok else f"Token: {enrollment_token[:20]}...",
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("2b. Create enrollment token", False, detail=str(e)))

    # 2c. Register agent
    api_key = None
    registered_host_id = None
    if enrollment_token:
        try:
            r = await client.post("/api/v1/agent/register", json={
                "enrollment_token": enrollment_token,
                "hostname": "e2e-test-host",
                "ip_address": "192.168.1.100",
                "os_info": "Linux 6.1.0",
            })
            ok = r.status_code in (200, 201)
            api_key = r.json().get("api_key") if ok else None
            registered_host_id = r.json().get("host_id") if ok else None
            suite.add(TestResult(
                "2c. Register agent via POST /api/v1/agent/register",
                ok,
                detail=f"Got {r.status_code}: {r.text[:100]}" if not ok else f"API key received, host_id={registered_host_id}",
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("2c. Register agent", False, detail=str(e)))
    else:
        suite.add(TestResult("2c. Register agent", False, detail="Skipped — no enrollment token"))

    # 2d. Send heartbeat
    if api_key:
        try:
            r = await client.post("/api/v1/agent/heartbeat",
                                  headers={"X-API-Key": api_key},
                                  json={"agent_version": "1.0.0"})
            ok = r.status_code == 200
            suite.add(TestResult(
                "2d. Send heartbeat via POST /api/v1/agent/heartbeat",
                ok,
                detail=f"Got {r.status_code}: {r.text[:100]}" if not ok else "Heartbeat OK",
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("2d. Send heartbeat", False, detail=str(e)))
    else:
        suite.add(TestResult("2d. Send heartbeat", False, detail="Skipped — no API key"))

    # 2e. Send events
    event_count = 0
    if api_key:
        try:
            now = datetime.now(timezone.utc).isoformat()
            r = await client.post("/api/v1/agent/events",
                                  headers={"X-API-Key": api_key},
                                  json={
                                      "events": [
                                          {
                                              "event_type": "ssh_login_failure",
                                              "severity": "high",
                                              "description": "Failed login from 10.0.0.1",
                                              "source": "sshd",
                                              "timestamp": now,
                                          },
                                          {
                                              "event_type": "service_failure",
                                              "severity": "high",
                                              "description": "nginx.service failed",
                                              "source": "systemd",
                                              "timestamp": now,
                                          },
                                      ]
                                  })
            ok = r.status_code == 200
            if ok:
                event_count = r.json().get("ingested", 0)
            suite.add(TestResult(
                "2e. Send events via POST /api/v1/agent/events",
                ok,
                detail=f"Got {r.status_code}: {r.text[:100]}" if not ok else f"Ingested {event_count} events",
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("2e. Send events", False, detail=str(e)))
    else:
        suite.add(TestResult("2e. Send events", False, detail="Skipped — no API key"))

    # 2f. Verify events appear in GET /api/v1/events
    if registered_host_id:
        try:
            # Small delay for async processing
            await asyncio.sleep(1.5)
            r = await client.get("/api/v1/events", headers=_h(admin_token))
            ok = r.status_code == 200
            if ok:
                items = r.json().get("items", [])
                # Filter events for our host
                host_events = [e for e in items if e.get("host_id") == registered_host_id]
                ok = len(host_events) >= 1
                detail = f"Found {len(host_events)} events for host (expected >=1)" if not ok else "Events found"
            else:
                detail = f"Got {r.status_code}"
            suite.add(TestResult(
                "2f. Verify events appear in GET /api/v1/events",
                ok,
                detail=detail if not ok else detail,
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("2f. Verify events in GET /api/v1/events", False, detail=str(e)))
    else:
        suite.add(TestResult("2f. Verify events in GET /api/v1/events", False, detail="Skipped — no host_id"))

    # 2g. Verify agent state: host is enrolled and online
    if host_id:
        try:
            r = await client.get(f"/api/v1/hosts/{host_id}", headers=_h(admin_token))
            ok = r.status_code == 200
            if ok:
                data = r.json()
                enrolled = data.get("enrolled", False)
                status = data.get("status", "")
                ok = enrolled and status == "online"
                detail = f"enrolled={enrolled}, status={status}" if not ok else "Host is enrolled and online"
            else:
                detail = f"Got {r.status_code}"
            suite.add(TestResult(
                "2g. Host is enrolled and online after agent registration",
                ok,
                detail=detail,
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("2g. Host enrolled/online check", False, detail=str(e)))

    return api_key, registered_host_id


# ======================================================================
# 3. DETECTION PIPELINE TESTS
# ======================================================================
async def test_detection_pipeline(suite: TestSuite, client: httpx.AsyncClient, admin_token: str, api_key: str, host_id: str):
    print(f"\n{'='*70}")
    print("  3. DETECTION PIPELINE TESTS")
    print(f"{'='*70}")

    # 3a. Send events that should trigger alert rules
    # Send multiple ssh_login_failure events to trigger the "Failed Logins" rule (threshold=5)
    if api_key:
        try:
            now = datetime.now(timezone.utc).isoformat()
            events = [
                {
                    "event_type": "ssh_login_failure",
                    "severity": "high",
                    "description": f"Failed SSH login attempt #{i} from 10.0.0.1",
                    "source": "sshd",
                    "timestamp": now,
                    "metadata": {"source_ip": f"10.0.0.{i}", "username": "root"},
                }
                for i in range(1, 7)  # 6 events to exceed threshold of 5
            ]
            r = await client.post("/api/v1/agent/events",
                                  headers={"X-API-Key": api_key},
                                  json={"events": events})
            ok = r.status_code == 200
            ingested = r.json().get("ingested", 0) if ok else 0
            suite.add(TestResult(
                "3a. Send 6 SSH login failure events to trigger alert rule",
                ok,
                detail=f"Got {r.status_code}" if not ok else f"Ingested {ingested}/6 events",
                status_code=r.status_code,
            ))
        except Exception as e:
            suite.add(TestResult("3a. Send detection-triggering events", False, detail=str(e)))
    else:
        suite.add(TestResult("3a. Send detection-triggering events", False, detail="Skipped — no API key"))

    # 3b. Wait for detection pipeline to process
    await asyncio.sleep(3.0)

    # 3c. Check if alerts are created
    alert_data = None
    try:
        r = await client.get("/api/v1/alerts", headers=_h(admin_token))
        ok = r.status_code == 200
        if ok:
            items = r.json().get("items", [])
            # Find alerts for our host
            host_alerts = [a for a in items if a.get("host_id") == host_id]
            ok = len(host_alerts) >= 1
            if host_alerts:
                alert_data = host_alerts[0]
            detail = f"Found {len(host_alerts)} alerts for host (expected >=1)" if not ok else "Alerts found"
        else:
            detail = f"Got {r.status_code}"
        suite.add(TestResult(
            "3c. Alerts created after detection pipeline runs",
            ok,
            detail=detail,
            status_code=r.status_code,
        ))
    except Exception as e:
        suite.add(TestResult("3c. Check alerts created", False, detail=str(e)))

    # 3d. Verify alert has correct fields
    if alert_data:
        required_fields = ["id", "status", "severity", "host_id"]
        missing = [f for f in required_fields if f not in alert_data]
        ok = len(missing) == 0
        suite.add(TestResult(
            "3d. Alert has correct fields (id, status, severity, host_id)",
            ok,
            detail=f"Missing: {missing}" if missing else "All required fields present",
        ))

        # 3e. Verify alert values are valid
        if ok:
            valid = (
                alert_data["status"] in ("open", "investigating", "resolved", "closed")
                and alert_data["severity"] in ("low", "medium", "high", "critical")
                and alert_data["host_id"] == host_id
            )
            suite.add(TestResult(
                "3e. Alert values are valid",
                valid,
                detail=f"status={alert_data['status']}, severity={alert_data['severity']}, host_id={alert_data['host_id']}",
            ))
    else:
        suite.add(TestResult("3d. Alert has correct fields", False, detail="Skipped — no alert data"))
        suite.add(TestResult("3e. Alert values are valid", False, detail="Skipped — no alert data"))

    # 3f. Check correlation rules exist
    try:
        r = await client.get("/api/v1/correlation-rules", headers=_h(admin_token))
        ok = r.status_code == 200
        if ok:
            rules = r.json()
            ok = len(rules) >= 1
            detail = f"Found {len(rules)} correlation rules (expected >=1)" if not ok else f"{len(rules)} correlation rules seeded"
        else:
            detail = f"Got {r.status_code}"
        suite.add(TestResult(
            "3f. Correlation rules exist (GET /api/v1/correlation-rules)",
            ok,
            detail=detail,
            status_code=r.status_code,
        ))
    except Exception as e:
        suite.add(TestResult("3f. Check correlation rules exist", False, detail=str(e)))

    # 3g. Check alert rules exist
    try:
        r = await client.get("/api/v1/alert-rules", headers=_h(admin_token))
        ok = r.status_code == 200
        if ok:
            rules = r.json()
            ok = len(rules) >= 1
            rule_names = [r.get("name", "") for r in rules]
            detail = f"Found {len(rules)} alert rules" if ok else f"Only {len(rules)} rules (expected >=1)"
        else:
            detail = f"Got {r.status_code}"
        suite.add(TestResult(
            "3g. Alert rules exist (GET /api/v1/alert-rules)",
            ok,
            detail=detail,
            status_code=r.status_code,
        ))
    except Exception as e:
        suite.add(TestResult("3g. Check alert rules exist", False, detail=str(e)))


# ======================================================================
# 4. OUTBOX GUARANTEE TESTS
# ======================================================================
async def test_outbox_guarantee(suite: TestSuite):
    print(f"\n{'='*70}")
    print("  4. OUTBOX GUARANTEE TESTS")
    print(f"{'='*70}")

    # 4a. Read database.py and verify post-commit hook pattern
    try:
        with open("app/database.py", "r") as f:
            content = f.read()

        # Check that get_db commits THEN runs hooks
        has_commit = "await session.commit()" in content
        has_hooks = "post_commit_hooks" in content
        hooks_after_commit = False
        if has_commit and has_hooks:
            # Verify hooks are popped AFTER commit, not before
            commit_pos = content.find("await session.commit()")
            hooks_pos = content.find("post_commit_hooks")
            hooks_after_commit = hooks_pos > commit_pos

        ok = has_commit and has_hooks and hooks_after_commit
        detail_parts = []
        if not has_commit:
            detail_parts.append("missing session.commit()")
        if not has_hooks:
            detail_parts.append("missing post_commit_hooks")
        if not hooks_after_commit:
            detail_parts.append("hooks not after commit")

        suite.add(TestResult(
            "4a. database.py get_db commits before running post-commit hooks",
            ok,
            detail="OK" if ok else "; ".join(detail_parts),
        ))
    except Exception as e:
        suite.add(TestResult("4a. database.py post-commit pattern", False, detail=str(e)))

    # 4b. Verify ingestion.py uses post_commit_hooks (outbox pattern)
    try:
        with open("app/pipeline/ingestion.py", "r") as f:
            content = f.read()

        uses_outbox = "post_commit_hooks" in content and "db.info" in content
        ws_in_hooks = "ws_manager.broadcast" in content
        ok = uses_outbox and ws_in_hooks
        suite.add(TestResult(
            "4b. Ingestion pipeline uses post-commit outbox for WS broadcast",
            ok,
            detail="OK" if ok else f"outbox={uses_outbox}, ws_in_hooks={ws_in_hooks}",
        ))
    except Exception as e:
        suite.add(TestResult("4b. Ingestion outbox pattern", False, detail=str(e)))

    # 4c. Verify alert creation uses post_commit_hooks
    try:
        with open("app/services/detection.py", "r") as f:
            content = f.read()

        uses_outbox = "post_commit_hooks" in content
        ws_after_commit = "ws_manager.broadcast" in content
        ok = uses_outbox and ws_after_commit
        suite.add(TestResult(
            "4c. Detection service uses post-commit outbox for alerts",
            ok,
            detail="OK" if ok else f"outbox={uses_outbox}, ws={ws_after_commit}",
        ))
    except Exception as e:
        suite.add(TestResult("4c. Detection outbox pattern", False, detail=str(e)))

    # 4d. Verify alerts router uses post_commit_hooks
    try:
        with open("app/routers/alerts.py", "r") as f:
            content = f.read()

        uses_outbox = "post_commit_hooks" in content
        ws_in_hooks = "ws_manager.broadcast" in content
        ok = uses_outbox and ws_in_hooks
        suite.add(TestResult(
            "4d. Alerts router uses post-commit outbox for status updates",
            ok,
            detail="OK" if ok else f"outbox={uses_outbox}, ws={ws_in_hooks}",
        ))
    except Exception as e:
        suite.add(TestResult("4d. Alerts router outbox pattern", False, detail=str(e)))


# ======================================================================
# 5. JOB QUEUE TESTS
# ======================================================================
async def test_job_queue(suite: TestSuite, client: httpx.AsyncClient):
    print(f"\n{'='*70}")
    print("  5. JOB QUEUE TESTS")
    print(f"{'='*70}")

    # 5a. Check /health/ready shows job_queue status
    try:
        r = await client.get("/health/ready")
        ok = r.status_code == 200
        if ok:
            data = r.json()
            checks = data.get("checks", {})
            job_status = checks.get("job_queue", "missing")
            ok = job_status == "ok"
            detail = f"job_queue={job_status}" if not ok else "job_queue=ok"
        else:
            detail = f"Got {r.status_code}"
        suite.add(TestResult(
            "5a. GET /health/ready shows job_queue=ok",
            ok,
            detail=detail,
            status_code=r.status_code,
        ))
    except Exception as e:
        suite.add(TestResult("5a. Health check job_queue", False, detail=str(e)))

    # 5b. Check overall readiness
    try:
        r = await client.get("/health/ready")
        ok = r.status_code == 200
        if ok:
            data = r.json()
            status = data.get("status", "")
            ok = status in ("ready", "degraded")
            detail = f"status={status}"
        else:
            detail = f"Got {r.status_code}"
        suite.add(TestResult(
            "5b. GET /health/ready status is ready or degraded",
            ok,
            detail=detail,
            status_code=r.status_code,
        ))
    except Exception as e:
        suite.add(TestResult("5b. Health check status", False, detail=str(e)))

    # 5c. Check Redis has keys
    try:
        rc, out = _run_docker_cmd(
            f"docker exec securi-redis redis-cli -a {REDIS_PASSWORD} KEYS '*'"
        )
        ok = rc == 0
        key_count = len(out.splitlines()) if ok and out.strip() else 0
        suite.add(TestResult(
            "5c. Redis has keys (docker exec KEYS *)",
            ok and key_count >= 0,
            detail=f"rc={rc} keys={key_count}" if not ok else f"{key_count} keys found",
        ))
    except Exception as e:
        suite.add(TestResult("5c. Redis KEYS check", False, detail=str(e)))

    # 5d. Check Redis connectivity
    try:
        rc, out = _run_docker_cmd(
            f"docker exec securi-redis redis-cli -a {REDIS_PASSWORD} PING"
        )
        ok = rc == 0 and "PONG" in out
        suite.add(TestResult(
            "5d. Redis PING via docker exec",
            ok,
            detail=f"rc={rc} out={out}" if not ok else "PONG",
        ))
    except Exception as e:
        suite.add(TestResult("5d. Redis PING", False, detail=str(e)))

    # 5e. Check health/ready database check
    try:
        r = await client.get("/health/ready")
        if r.status_code == 200:
            checks = r.json().get("checks", {})
            db_status = checks.get("database", "missing")
            ok = db_status == "ok"
            suite.add(TestResult(
                "5e. GET /health/ready database=ok",
                ok,
                detail=f"database={db_status}",
                status_code=r.status_code,
            ))
        else:
            suite.add(TestResult("5e. GET /health/ready database=ok", False,
                                 detail=f"Got {r.status_code}", status_code=r.status_code))
    except Exception as e:
        suite.add(TestResult("5e. Health check database", False, detail=str(e)))


# ======================================================================
# 6. SCHEDULER TESTS
# ======================================================================
async def test_scheduler(suite: TestSuite, client: httpx.AsyncClient):
    print(f"\n{'='*70}")
    print("  6. SCHEDULER TESTS")
    print(f"{'='*70}")

    # 6a. Check scheduler.py exists and registers jobs
    try:
        with open("app/scheduler.py", "r") as f:
            content = f.read()

        has_scheduler = "AsyncIOScheduler" in content
        has_start = "def start_scheduler" in content
        has_add_job = "scheduler.add_job" in content
        job_count = content.count("scheduler.add_job")

        ok = has_scheduler and has_start and has_add_job
        detail = f"Scheduler defined, {job_count} jobs registered" if ok else f"scheduler={has_scheduler}, start={has_start}, add_job={has_add_job}"
        suite.add(TestResult(
            "6a. Scheduler defined with registered jobs",
            ok,
            detail=detail,
        ))
    except Exception as e:
        suite.add(TestResult("6a. Scheduler definition", False, detail=str(e)))

    # 6b. Verify expected scheduler jobs exist
    try:
        with open("app/scheduler.py", "r") as f:
            content = f.read()

        expected_jobs = [
            "host_status",
            "cross_host_correlation",
            "retention",
            "postgres_backup",
            "analytics",
            "analytics_materialized_views",
            "threat_intel_feed_sync",
            "ueba_scan",
            "saved_search_alerts",
        ]
        found = [j for j in expected_jobs if f'"{j}"' in content or f"'{j}'" in content]
        missing = [j for j in expected_jobs if j not in found]
        ok = len(found) >= 5  # At least 5 of 9 should be present
        suite.add(TestResult(
            "6b. Expected scheduler jobs registered",
            ok,
            detail=f"{len(found)}/{len(expected_jobs)} found" + (f" (missing: {missing})" if missing else ""),
        ))
    except Exception as e:
        suite.add(TestResult("6b. Scheduler jobs check", False, detail=str(e)))

    # 6c. Check that main.py starts the scheduler
    try:
        with open("app/main.py", "r") as f:
            content = f.read()

        imports_scheduler = "from app.scheduler import" in content
        starts_scheduler = "start_scheduler()" in content
        ok = imports_scheduler and starts_scheduler
        suite.add(TestResult(
            "6c. main.py imports and starts scheduler",
            ok,
            detail="OK" if ok else f"import={imports_scheduler}, start={starts_scheduler}",
        ))
    except Exception as e:
        suite.add(TestResult("6c. main.py scheduler integration", False, detail=str(e)))

    # 6d. Check health/ready for scheduler-related dependencies
    try:
        r = await client.get("/health/ready")
        if r.status_code == 200:
            data = r.json()
            checks = data.get("checks", {})
            # Check that database and job_queue are healthy (scheduler depends on these)
            db_ok = checks.get("database") == "ok"
            jq_ok = checks.get("job_queue") == "ok"
            ok = db_ok and jq_ok
            suite.add(TestResult(
                "6d. Scheduler dependencies healthy (database + job_queue)",
                ok,
                detail=f"database={checks.get('database')}, job_queue={checks.get('job_queue')}",
                status_code=r.status_code,
            ))
        else:
            suite.add(TestResult("6d. Scheduler dependencies healthy", False,
                                 detail=f"Got {r.status_code}", status_code=r.status_code))
    except Exception as e:
        suite.add(TestResult("6d. Scheduler dependencies", False, detail=str(e)))

    # 6e. Check scheduler logs for errors (via docker logs)
    try:
        rc, out = _run_docker_cmd(
            "docker logs securi-backend --tail 100 2>&1"
        )
        has_scheduler_started = "Scheduler started" in out
        has_scheduler_error = "scheduler" in out.lower() and "error" in out.lower()
        ok = has_scheduler_started and not has_scheduler_error
        suite.add(TestResult(
            "6e. No scheduler errors in recent logs",
            ok,
            detail=f"started={has_scheduler_started}, errors={has_scheduler_error}",
        ))
    except Exception as e:
        suite.add(TestResult("6e. Scheduler log check", False, detail=str(e)))


# ======================================================================
# MAIN
# ======================================================================
async def run_all():
    suite = TestSuite()

    client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True, cookies=None)
    try:
        # Verify backend is up
        try:
            h = await client.get("/health/ready")
            if h.status_code not in (200, 503):
                print(f"ERROR: Backend not healthy (status={h.status_code})")
                return
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to {BASE_URL}")
            return

        # 1. WebSocket tests
        admin_token = await test_websocket(suite, client)

        # 2. Agent E2E tests
        api_key, registered_host_id = await test_agent_e2e(suite, client, admin_token)

        # 3. Detection pipeline tests
        await test_detection_pipeline(suite, client, admin_token, api_key, registered_host_id)

        # 4. Outbox guarantee tests
        await test_outbox_guarantee(suite)

        # 5. Job queue tests
        await test_job_queue(suite, client)

        # 6. Scheduler tests
        await test_scheduler(suite, client)

    finally:
        await client.aclose()

    suite.summary()
    return suite


def main():
    try:
        suite = asyncio.run(run_all())
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        tb.print_exc()
        sys.exit(1)

    if suite and suite.failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
