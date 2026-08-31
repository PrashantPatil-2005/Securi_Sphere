"""Debug script to reproduce the 500 error."""
import asyncio
import httpx
from datetime import datetime, timezone

async def debug():
    c = httpx.AsyncClient(base_url='http://127.0.0.1:8000', timeout=30.0)
    # Login
    r = await c.post('/api/v1/auth/login', json={'email': 'admin@test.local', 'password': 'testpass123'})
    token = r.json().get('access_token')
    print(f'Login: {r.status_code}')

    # Create host
    r = await c.post('/api/v1/hosts', json={'name': 'debug-host'}, headers={'Authorization': f'Bearer {token}'})
    print(f'Create host: {r.status_code} {r.json().get("id")}')
    host_id = r.json().get('id')

    # Create enrollment
    r = await c.post(f'/api/v1/hosts/{host_id}/enrollment-token', headers={'Authorization': f'Bearer {token}'})
    print(f'Enrollment token: {r.status_code}')
    et = r.json().get('token')

    # Register agent
    r = await c.post('/api/v1/agent/register', json={'enrollment_token': et, 'hostname': 'debug', 'ip_address': '10.0.0.5'})
    print(f'Agent register: {r.status_code} {r.json()}')
    api_key = r.json().get('api_key')

    # Send event
    now = datetime.now(timezone.utc).isoformat()
    r = await c.post('/api/v1/agent/events',
        headers={'X-API-Key': api_key},
        json={'events': [{'event_type': 'ssh_login_failure', 'severity': 'high', 'description': 'test fail', 'timestamp': now}]})
    print(f'Send event: {r.status_code} {r.text[:500]}')

    await c.aclose()

asyncio.run(debug())
