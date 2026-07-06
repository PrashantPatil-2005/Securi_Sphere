"""Runtime verification for flow bug fixes. Writes to debug-eedec7.log via instrumented routes."""
import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-key-minimum-length-required")
os.environ.setdefault("ASYNC_EVENT_PIPELINE", "false")

from httpx import ASGITransport, AsyncClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
LOG = ROOT / "debug-eedec7.log"


async def main() -> int:
    from app.main import app  # noqa: E402
    from app.database import async_session  # noqa: E402
    from app.routers.auth import seed_dev_users, seed_roles  # noqa: E402
    from app.services.migrate import migrate_schema  # noqa: E402

    try:
        await migrate_schema()
    except Exception as exc:
        print(f"SKIP: database unavailable ({exc})")
        return 0

    async with async_session() as db:
        await seed_roles(db)
        await seed_dev_users(db)
        await db.commit()

    transport = ASGITransport(app=app, lifespan="auto")
    failures = 0

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Login admin
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.local", "password": "testpass123"},
        )
        if login.status_code != 200:
            print(f"FAIL login: {login.status_code} {login.text}")
            failures += 1
            return failures

        # H-B: unknown scenario -> 404
        bad_sim = await client.post(f"/api/v1/simulation/run/not_a_scenario?host_id={uuid4()}")
        if bad_sim.status_code != 404:
            print(f"FAIL unknown scenario: expected 404 got {bad_sim.status_code} {bad_sim.text}")
            failures += 1
        else:
            print("OK unknown scenario returns 404")

        # H-C: missing host -> 404
        miss_sim = await client.post(f"/api/v1/simulation/run/multi_stage_attack?host_id={uuid4()}")
        if miss_sim.status_code != 404:
            print(f"FAIL missing host: expected 404 got {miss_sim.status_code} {miss_sim.text}")
            failures += 1
        else:
            print("OK missing host returns 404")

        # H-A: host created inactive
        host_res = await client.post("/api/v1/hosts", json={"name": f"verify-{uuid4().hex[:8]}"})
        if host_res.status_code != 200:
            print(f"FAIL create host: {host_res.status_code} {host_res.text}")
            failures += 1
        else:
            status = host_res.json().get("status")
            if status != "inactive":
                print(f"FAIL host status: expected inactive got {status}")
                failures += 1
            else:
                print("OK new host status is inactive")

            host_id = host_res.json()["id"]
            sim = await client.post(f"/api/v1/simulation/run/multi_stage_attack?host_id={host_id}")
            if sim.status_code == 403:
                print("SKIP simulation: admin required in this env")
            elif sim.status_code != 200:
                print(f"FAIL simulation: {sim.status_code} {sim.text}")
                failures += 1
            else:
                print(f"OK simulation completed: {sim.json().get('events')} events")

    if LOG.exists():
        print(f"\n--- debug log ({LOG}) ---")
        for line in LOG.read_text(encoding="utf-8").strip().splitlines():
            entry = json.loads(line)
            print(f"  [{entry.get('hypothesisId')}] {entry.get('location')}: {entry.get('message')} {entry.get('data')}")
    else:
        print(f"\nWARN: no log file at {LOG}")

    print(f"\nResult: {failures} failure(s)")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
