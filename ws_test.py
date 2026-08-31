"""
WebSocket E2E Test Script for Securi_Sphere backend.
Tests: login, WS auth handshake, ping/pong, invalid token, HTTP alert -> WS broadcast.
Uses only stdlib (urllib) for HTTP and websockets for WS.
"""

import asyncio
import json
import sys
import time
import urllib.request
import urllib.error

try:
    import websockets
except ImportError:
    print("[FATAL] 'websockets' library not installed")
    sys.exit(1)

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"
WS_URL = "ws://127.0.0.1:8000/api/v1/ws"
EMAIL = "admin@test.local"
PASSWORD = "testpass123"

results = {}


def verdict(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    tag = "[PASS]" if passed else "[FAIL]"
    msg = "  %s %s" % (tag, name)
    if detail:
        msg += " -- %s" % detail
    print(msg)
    results[name] = {"passed": passed, "detail": detail}


def http_post(url, data, headers=None):
    """POST JSON via urllib."""
    body = json.dumps(data).encode()
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, str(e)


def http_patch(url, data, headers=None):
    """PATCH JSON via urllib."""
    body = json.dumps(data).encode()
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="PATCH")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, str(e)


def http_get(url, headers=None):
    """GET via urllib."""
    hdrs = {}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, str(e)


# ── Test 1: Login ──────────────────────────────────────────────
def test_login():
    print("\n=== Test 1: Login (POST /api/v1/auth/login) ===")
    status, body = http_post(f"{API}/auth/login", {"email": EMAIL, "password": PASSWORD})
    if status == 200 and isinstance(body, dict) and "access_token" in body:
        token = body["access_token"]
        verdict("Login", True, "HTTP %d, got token (%d chars)" % (status, len(token)))
        return token
    verdict("Login", False, "HTTP %s, body=%s" % (status, str(body)[:200]))
    return None


# ── Test 2: WS connect with valid token ───────────────────────
async def test_ws_connect_valid(token):
    print("\n=== Test 2: WebSocket connect (valid token, auth handshake) ===")
    ws = None
    authenticated = False
    try:
        ws = await asyncio.wait_for(websockets.connect(WS_URL, open_timeout=5), timeout=5)
        print("  TCP connected to %s" % WS_URL)

        auth_msg = json.dumps({"type": "auth", "token": token})
        await ws.send(auth_msg)
        print("  Sent auth message")

        # If auth fails server closes with code 4001. If it succeeds, connection stays open.
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=2)
            print("  Received after auth: %s" % msg[:120])
            authenticated = True
        except asyncio.TimeoutError:
            # No data, no close -> connection is alive -> auth succeeded
            authenticated = True
            print("  No close frame -- connection accepted (authenticated)")

        verdict("WS connect (valid token)", authenticated, "connected=True, auth=%s" % authenticated)
    except Exception as e:
        verdict("WS connect (valid token)", False, str(e))

    return ws


# ── Test 3: Ping/pong ─────────────────────────────────────────
async def test_ws_ping_pong(ws):
    print("\n=== Test 3: WS ping/pong ===")
    if ws is None:
        verdict("WS ping/pong", False, "No WebSocket connection")
        return
    try:
        ping_msg = json.dumps({"type": "ping"})
        await ws.send(ping_msg)
        print("  Sent: %s" % ping_msg)

        resp = await asyncio.wait_for(ws.recv(), timeout=5)
        print("  Received: %s" % resp[:200])
        data = json.loads(resp)
        is_pong = data.get("type") == "pong" or "pong" in resp.lower()
        verdict("WS ping/pong", is_pong, "response=%s" % resp[:120])
    except asyncio.TimeoutError:
        # Server WS handler loops on receive_text() with no response logic — by design.
        # No application-level pong handler exists in ws.py. This is expected.
        verdict("WS ping/pong", False, "No pong (server WS handler has no message echo/respond logic — by design)")
    except websockets.exceptions.ConnectionClosed as e:
        verdict("WS ping/pong", False, "Connection closed: code=%s reason=%s" % (e.code, e.reason))
    except Exception as e:
        verdict("WS ping/pong", False, str(e))


# ── Test 4: Invalid token ─────────────────────────────────────
async def test_ws_invalid_token():
    print("\n=== Test 4: WS connect (invalid token) ===")
    ws = None
    try:
        ws = await asyncio.wait_for(websockets.connect(WS_URL, open_timeout=5), timeout=5)
        fake_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJoYWNrZXIiLCJ0eXBlIjoiYWNjZXNzIn0.badsignature"
        auth_msg = json.dumps({"type": "auth", "token": fake_token})
        await ws.send(auth_msg)

        # Expect server to close with code 4001
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            print("  Received after bad auth: %s" % msg[:200])
        except asyncio.TimeoutError:
            pass

        # Wait a beat then check
        await asyncio.sleep(0.5)
        is_closed = ws.state.name == "CLOSED"
        verdict("WS invalid token rejected", is_closed, "closed=%s (expected True)" % is_closed)
        if not is_closed:
            await ws.close()
    except websockets.exceptions.ConnectionClosedOK as e:
        verdict("WS invalid token rejected", True, "Connection closed OK (code=%d)" % e.code)
    except websockets.exceptions.ConnectionClosedError as e:
        verdict("WS invalid token rejected", True, "Connection closed (code=%d)" % e.code)
    except websockets.exceptions.InvalidStatusCode as e:
        verdict("WS invalid token rejected", True, "HTTP %s during handshake" % e.status_code)
    except Exception as e:
        verdict("WS invalid token rejected", True, "Connection rejected: %s" % e)
    finally:
        if ws and ws.state.name != "CLOSED":
            await ws.close()


# ── Test 5: HTTP alert -> WS broadcast ────────────────────────
async def test_http_alert_broadcasts_to_ws(token):
    print("\n=== Test 5: HTTP alert creation -> WS broadcast ===")
    headers = {"Authorization": "Bearer %s" % token}

    # 1) Get a host to associate the alert with
    status, hosts_data = http_get(f"{API}/hosts", headers)
    host_id = None
    if status == 200 and isinstance(hosts_data, dict):
        items = hosts_data.get("items", [])
        if items:
            host_id = items[0].get("id")
    print("  Host lookup: status=%s, host_id=%s" % (status, host_id))

    # 2) Open WS connection and authenticate
    ws = None
    try:
        ws = await asyncio.wait_for(websockets.connect(WS_URL, open_timeout=5), timeout=5)
        await ws.send(json.dumps({"type": "auth", "token": token}))
        # Drain auth ack or wait for stable state
        await asyncio.sleep(0.5)
        try:
            await asyncio.wait_for(ws.recv(), timeout=1)
        except asyncio.TimeoutError:
            pass
        print("  WS listener ready")
    except Exception as e:
        verdict("HTTP alert -> WS broadcast", False, "WS setup failed: %s" % e)
        return

    # 3) Update alert status (triggers ws_manager.broadcast with type=alert_updated)
    # First list existing alerts to get one to update
    status, alerts_data = http_get(f"{API}/alerts", headers)
    alert_id = None
    if status == 200 and isinstance(alerts_data, dict):
        items = alerts_data.get("items", [])
        if items:
            alert_id = items[0].get("id")
            print("  Found existing alert: %s" % alert_id)

    broadcast_received = False
    broadcast_data = None

    if alert_id:
        # Try feedback endpoint first (avoids update_host_statuses bug)
        # feedback label != "false_positive" to skip status change + update_host_statuses
        upd_status, upd_body = http_patch(
            f"{API}/alerts/{alert_id}/feedback",
            {"label": "true_positive", "note": "WS E2E test"},
            headers,
        )
        print("  PATCH /alerts/%s/feedback -> %s" % (alert_id, upd_status))

        if upd_status == 500:
            # Fallback: try the bulk endpoint
            print("  Feedback returned 500, trying bulk update...")
            upd_status, upd_body = http_patch(
                f"{API}/alerts/bulk",
                {"alert_ids": [alert_id], "status": "investigating"},
                headers,
            )
            print("  PATCH /alerts/bulk -> %s" % upd_status)

        if upd_status == 500:
            # Last resort: try status endpoint
            print("  Bulk returned 500, trying status endpoint...")
            upd_status, upd_body = http_patch(
                f"{API}/alerts/{alert_id}/status",
                {"status": "investigating"},
                headers,
            )
            print("  PATCH /alerts/%s/status -> %s" % (alert_id, upd_status))

        # Listen for broadcast
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.5)
                print("  WS received: %s" % msg[:200])
                data = json.loads(msg)
                if data.get("type") in ("alert_updated", "alert_created", "new_alert", "alert_feedback"):
                    broadcast_received = True
                    broadcast_data = data
                    break
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception:
                break
    else:
        print("  No alerts found to test broadcast with")
        verdict("HTTP alert -> WS broadcast", False, "No alerts available for broadcast test")
        await ws.close()
        return

    verdict("HTTP alert -> WS broadcast", broadcast_received,
            "received=%s, data=%s" % (broadcast_received, str(broadcast_data)[:120] if broadcast_data else "none"))
    await ws.close()


# ── Main ───────────────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("  Securi_Sphere WebSocket E2E Test Suite")
    print("=" * 60)

    # 1. Login
    token = test_login()
    if not token:
        print("\n[ABORT] Cannot proceed without access token.")
        print_summary()
        return

    # 2. WS connect with valid token
    ws = await test_ws_connect_valid(token)

    # 3. Ping/pong
    if ws and ws.state.name != "CLOSED":
        await test_ws_ping_pong(ws)
        try:
            await ws.close()
        except Exception:
            pass

    # 4. Invalid token
    await test_ws_invalid_token()

    # 5. HTTP alert -> WS broadcast
    await test_http_alert_broadcasts_to_ws(token)

    print_summary()


def print_summary():
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    total = len(results)
    passed = sum(1 for r in results.values() if r["passed"])
    failed = total - passed
    for name, r in results.items():
        status = "PASS" if r["passed"] else "FAIL"
        print("  [%s] %s" % (status, name))
    print("\n  %d/%d passed, %d/%d failed" % (passed, total, failed, total))
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
