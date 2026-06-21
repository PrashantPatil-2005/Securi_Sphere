import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.models.event import Event
from app.models.host import Host
from app.models.user import User
from app.services.audit import log_audit
from app.services.detection import run_detection_for_host
from app.services.mitre import enrich_event
from app.services.correlation_engine import run_correlation_engine
from app.services.timeline import build_timelines

router = APIRouter(prefix="/simulation", tags=["simulation"])

SCENARIOS = {
    "brute_force": [
        ("ssh_login_failure", 0), ("ssh_login_failure", 30), ("ssh_login_failure", 60),
        ("ssh_login_success", 120), ("sudo_usage", 150),
    ],
    "brute_force_only": [("ssh_login_failure", i * 20) for i in range(6)],
    "service_crash": [("service_failure", 0)],
}


@router.get("/scenarios")
async def list_scenarios(user: User = Depends(require_roles("admin"))):
    return {"scenarios": list(SCENARIOS.keys())}


@router.post("/run/{scenario}")
async def run_simulation(scenario: str, host_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("admin"))):
    if not settings.enable_simulation:
        raise HTTPException(status_code=403, detail="Simulation disabled in this environment")
    if scenario not in SCENARIOS:
        return {"error": "unknown scenario"}
    host = (await db.execute(__import__("sqlalchemy").select(Host).where(Host.id == host_id))).scalar_one()
    now = datetime.now(timezone.utc)
    for etype, offset in SCENARIOS[scenario]:
        event = Event(
            host_id=host_id, event_type=etype, severity="medium" if "failure" in etype else "high",
            description=f"[SIMULATED] {etype}", source="simulation",
            timestamp=now + timedelta(seconds=offset),
            metadata_={"simulated": True},
        )
        enrich_event(event)
        db.add(event)
    await db.flush()
    await run_detection_for_host(db, host)
    await run_correlation_engine(db, host_id)
    await build_timelines(db, host_id)
    await log_audit(db, "simulation_run", user_id=user.id, details={"scenario": scenario, "host_id": str(host_id)})
    return {"message": f"Simulation {scenario} completed", "events": len(SCENARIOS[scenario])}
