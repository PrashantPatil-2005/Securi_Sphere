"""SOAR playbooks API — webhook automation on security events."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_roles
from app.models.playbook import Playbook, PlaybookRun
from app.models.user import User
from app.schemas.playbook import (
    PlaybookCreate,
    PlaybookResponse,
    PlaybookRunResponse,
    PlaybookTestResponse,
    PlaybookUpdate,
)
from app.services.audit import log_audit
from app.services.playbooks import send_test_webhook, validate_min_severity, validate_trigger

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


def _to_response(pb: Playbook) -> PlaybookResponse:
    return PlaybookResponse(
        id=pb.id,
        name=pb.name,
        description=pb.description,
        trigger_event=pb.trigger_event,
        min_severity=pb.min_severity,
        webhook_url=pb.webhook_url,
        has_secret=bool(pb.webhook_secret),
        enabled=pb.enabled,
        created_at=pb.created_at,
        updated_at=pb.updated_at,
    )


@router.get("", response_model=list[PlaybookResponse])
async def list_playbooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    rows = list((await db.execute(select(Playbook).order_by(Playbook.name))).scalars().all())
    return [_to_response(pb) for pb in rows]


@router.post("", response_model=PlaybookResponse, status_code=201)
async def create_playbook(
    body: PlaybookCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    existing = (await db.execute(select(Playbook).where(Playbook.name == body.name.strip()))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Playbook name already exists")
    try:
        validate_trigger(body.trigger_event)
        validate_min_severity(body.min_severity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pb = Playbook(
        name=body.name.strip(),
        description=body.description,
        trigger_event=body.trigger_event,
        min_severity=body.min_severity,
        webhook_url=body.webhook_url.strip(),
        webhook_secret=body.webhook_secret,
        enabled=body.enabled,
    )
    db.add(pb)
    await db.flush()
    await log_audit(db, "playbook_created", user_id=user.id, details={"name": pb.name, "trigger": pb.trigger_event})
    return _to_response(pb)


@router.patch("/{playbook_id}", response_model=PlaybookResponse)
async def update_playbook(
    playbook_id: UUID,
    body: PlaybookUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    pb = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    if body.trigger_event is not None:
        try:
            validate_trigger(body.trigger_event)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        pb.trigger_event = body.trigger_event
    if body.min_severity is not None:
        try:
            pb.min_severity = validate_min_severity(body.min_severity)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.description is not None:
        pb.description = body.description
    if body.webhook_url is not None:
        pb.webhook_url = body.webhook_url.strip()
    if body.webhook_secret is not None:
        pb.webhook_secret = body.webhook_secret or None
    if body.enabled is not None:
        pb.enabled = body.enabled
    await db.flush()
    return _to_response(pb)


@router.delete("/{playbook_id}", status_code=204)
async def delete_playbook(
    playbook_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    pb = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    await db.delete(pb)
    await log_audit(db, "playbook_deleted", user_id=user.id, details={"name": pb.name})


@router.get("/{playbook_id}/runs", response_model=list[PlaybookRunResponse])
async def list_playbook_runs(
    playbook_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    pb = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    runs = list(
        (
            await db.execute(
                select(PlaybookRun)
                .where(PlaybookRun.playbook_id == playbook_id)
                .order_by(PlaybookRun.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    )
    return runs


@router.post("/{playbook_id}/test", response_model=PlaybookTestResponse)
async def test_playbook(
    playbook_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin", "analyst")),
):
    pb = (await db.execute(select(Playbook).where(Playbook.id == playbook_id))).scalar_one_or_none()
    if not pb:
        raise HTTPException(status_code=404, detail="Playbook not found")
    run = await send_test_webhook(pb)
    db.add(run)
    await db.flush()
    return PlaybookTestResponse(status=run.status, http_status=run.http_status, error_message=run.error_message)
