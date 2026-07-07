"""SOAR playbook matching, webhook dispatch, and audit."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brand import PRODUCT_NAME
from app.core.circuit_breaker import CircuitOpenError
from app.core.circuit_guard import run_async
from app.core.http_timeouts import outbound_timeout

from app.models.alert import Alert
from app.models.incident import Incident
from app.models.playbook import PLAYBOOK_TRIGGERS, SEVERITY_LEVELS, Playbook, PlaybookRun
from app.models.siem import Offense

logger = logging.getLogger(__name__)

SEVERITY_RANK = {name: idx for idx, name in enumerate(SEVERITY_LEVELS)}


def validate_trigger(trigger: str) -> str:
    if trigger not in PLAYBOOK_TRIGGERS:
        raise ValueError(f"trigger_event must be one of: {', '.join(sorted(PLAYBOOK_TRIGGERS))}")
    return trigger


def validate_min_severity(severity: str | None) -> str | None:
    if severity is None:
        return None
    if severity not in SEVERITY_LEVELS:
        raise ValueError(f"min_severity must be one of: {', '.join(SEVERITY_LEVELS)}")
    return severity


def severity_meets_minimum(actual: str | None, minimum: str | None) -> bool:
    if not minimum:
        return True
    if not actual:
        return False
    return SEVERITY_RANK.get(actual, 0) >= SEVERITY_RANK.get(minimum, 0)


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def schedule_playbook_dispatch(
    event: str,
    resource_type: str,
    resource_id: UUID | str,
    **extra: Any,
) -> None:
    from app.jobs.queue import job_queue

    await job_queue.enqueue(
        "playbook_dispatch",
        {
            "event": event,
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            **extra,
        },
    )


async def _serialize_alert(alert: Alert) -> dict:
    return {
        "id": str(alert.id),
        "host_id": str(alert.host_id),
        "title": alert.title,
        "description": alert.description,
        "severity": alert.severity,
        "status": alert.status,
        "confidence": alert.confidence,
        "mitre_technique_id": alert.mitre_technique_id,
        "mitre_tactic": alert.mitre_tactic,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
    }


async def _serialize_offense(offense: Offense) -> dict:
    return {
        "id": str(offense.id),
        "offense_number": offense.offense_number,
        "host_id": str(offense.host_id) if offense.host_id else None,
        "title": offense.title,
        "description": offense.description,
        "risk_level": offense.risk_level,
        "status": offense.status,
        "event_count": offense.event_count,
        "alert_count": offense.alert_count,
        "incident_id": str(offense.incident_id) if offense.incident_id else None,
        "created_at": offense.created_at.isoformat() if offense.created_at else None,
    }


async def _serialize_incident(incident: Incident) -> dict:
    return {
        "id": str(incident.id),
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "host_id": str(incident.host_id) if incident.host_id else None,
        "created_by": str(incident.created_by) if incident.created_by else None,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


async def build_event_payload(
    db: AsyncSession,
    event: str,
    resource_type: str,
    resource_id: str,
    **extra: Any,
) -> dict | None:
    rid = UUID(resource_id)
    data: dict | None = None

    if resource_type == "alert":
        alert = await db.get(Alert, rid)
        if alert:
            data = await _serialize_alert(alert)
    elif resource_type == "offense":
        offense = await db.get(Offense, rid)
        if offense:
            data = await _serialize_offense(offense)
    elif resource_type == "incident":
        incident = await db.get(Incident, rid)
        if incident:
            data = await _serialize_incident(incident)

    if data is None:
        return None

    payload: dict[str, Any] = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "data": data,
    }
    if extra:
        payload["context"] = extra
    return payload


def _playbook_matches(playbook: Playbook, event: str, severity: str | None) -> bool:
    if not playbook.enabled or playbook.trigger_event != event:
        return False
    return severity_meets_minimum(severity, playbook.min_severity)


def _severity_for_payload(event: str, payload: dict) -> str | None:
    data = payload.get("data") or {}
    if event.startswith("alert"):
        return data.get("severity")
    if event.startswith("offense"):
        return data.get("risk_level")
    if event.startswith("incident"):
        return data.get("severity")
    return None


async def execute_matching_playbooks(db: AsyncSession, event: str, payload: dict) -> list[PlaybookRun]:
    playbooks = list(
        (await db.execute(select(Playbook).where(Playbook.enabled.is_(True), Playbook.trigger_event == event))).scalars().all()
    )
    severity = _severity_for_payload(event, payload)
    runs: list[PlaybookRun] = []

    for playbook in playbooks:
        if not _playbook_matches(playbook, event, severity):
            continue
        run = await _deliver_webhook(db, playbook, event, payload)
        runs.append(run)

    return runs


async def _deliver_webhook(
    db: AsyncSession,
    playbook: Playbook,
    event: str,
    payload: dict,
) -> PlaybookRun:
    body = json.dumps(payload, default=str).encode()
    headers = {"Content-Type": "application/json", "User-Agent": f"{PRODUCT_NAME}-Playbook/1.0"}
    if playbook.webhook_secret:
        headers["X-Securi-Signature"] = sign_payload(playbook.webhook_secret, body)

    status = "failed"
    http_status: int | None = None
    error_message: str | None = None

    try:
        async def _post():
            async with httpx.AsyncClient(timeout=outbound_timeout(short=True)) as client:
                return await client.post(playbook.webhook_url, content=body, headers=headers)

        response = await run_async("playbook_webhook", _post)
        http_status = response.status_code
        if 200 <= response.status_code < 300:
            status = "success"
        else:
            error_message = (response.text or "")[:500]
    except CircuitOpenError:
        error_message = "circuit_open"
    except Exception as exc:
        error_message = str(exc)[:500]
        logger.warning(
            "playbook webhook failed",
            extra={"playbook": playbook.name, "event": event, "error": error_message},
        )

    run = PlaybookRun(
        playbook_id=playbook.id,
        trigger_event=event,
        status=status,
        http_status=http_status,
        error_message=error_message,
        payload=payload,
    )
    db.add(run)
    await db.flush()
    return run


async def dispatch_playbook_event(
    db: AsyncSession,
    event: str,
    resource_type: str,
    resource_id: str,
    **extra: Any,
) -> list[PlaybookRun]:
    payload = await build_event_payload(db, event, resource_type, resource_id, **extra)
    if not payload:
        return []
    return await execute_matching_playbooks(db, event, payload)


async def send_test_webhook(playbook: Playbook) -> PlaybookRun:
    payload = {
        "event": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resource_type": "playbook",
        "resource_id": str(playbook.id),
        "data": {
            "name": playbook.name,
            "trigger_event": playbook.trigger_event,
            "message": f"{PRODUCT_NAME} playbook test ping",
        },
    }
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": f"{PRODUCT_NAME}-Playbook/1.0"}
    if playbook.webhook_secret:
        headers["X-Securi-Signature"] = sign_payload(playbook.webhook_secret, body)

    status = "failed"
    http_status: int | None = None
    error_message: str | None = None
    try:
        async def _post():
            async with httpx.AsyncClient(timeout=outbound_timeout(short=True)) as client:
                return await client.post(playbook.webhook_url, content=body, headers=headers)

        response = await run_async("playbook_webhook", _post)
        http_status = response.status_code
        status = "success" if 200 <= response.status_code < 300 else "failed"
        if status != "success":
            error_message = (response.text or "")[:500]
    except CircuitOpenError:
        error_message = "circuit_open"
    except Exception as exc:
        error_message = str(exc)[:500]

    return PlaybookRun(
        playbook_id=playbook.id,
        trigger_event="test",
        status=status,
        http_status=http_status,
        error_message=error_message,
        payload=payload,
    )
