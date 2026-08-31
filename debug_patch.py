"""Debug: test PATCH alert status and check for 500 error."""
import urllib.request, urllib.error, json

BASE = "http://127.0.0.1:8000/api/v1"

def do(url, method="GET", data=None, headers=None):
    hdrs = headers or {}
    body = json.dumps(data).encode() if data else None
    if data:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            body = json.loads(raw)
        except Exception:
            body = raw
        return e.code, body

# Login
status, body = do(f"{BASE}/auth/login", "POST", {"email": "admin@test.local", "password": "testpass123"})
token = body["access_token"]
auth = {"Authorization": f"Bearer {token}"}
print("Login:", status)

# List hosts
status, hosts = do(f"{BASE}/hosts", headers=auth)
for h in hosts.get("items", []):
    print(f"  Host {h['id']}: status={h['status']}, name={h.get('hostname', '?')}")

# List alerts
status, alerts = do(f"{BASE}/alerts", headers=auth)
for a in alerts.get("items", []):
    print(f"  Alert {a['id']}: status={a['status']}, host_id={a.get('host_id')}, severity={a.get('severity')}")

# Try PATCH status on first alert with different values
alert_id = alerts["items"][0]["id"]
current = alerts["items"][0]["status"]
print(f"\nPatching alert {alert_id} (current={current})")

# Try: open -> investigating
for target in ["investigating", "resolved", "open"]:
    print(f"\n  Trying {current} -> {target}:")
    s, b = do(f"{BASE}/alerts/{alert_id}/status", "PATCH", {"status": target}, auth)
    print(f"    Status: {s}")
    if s != 200:
        print(f"    Body: {json.dumps(b)[:300]}")
    else:
        print(f"    OK: status={b.get('status')}")
