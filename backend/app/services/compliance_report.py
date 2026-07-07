"""Compliance report assembly and PDF export."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.audit import AuditLog
from app.models.event import Event
from app.models.host import Host
from app.models.incident import Incident
from app.models.playbook import Playbook
from app.models.role import Role
from app.models.siem import Offense
from app.models.ueba import UebaAnomaly
from app.models.user import User
from app.services.compliance_templates import COMPLIANCE_FRAMEWORKS, evaluate_framework, list_frameworks
from app.services.executive_report import period_bounds


async def gather_compliance_evidence(db: AsyncSession, start: datetime, end: datetime) -> dict[str, Any]:
    audit_events_period = (
        await db.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.timestamp >= start, AuditLog.timestamp <= end)
        )
    ).scalar_one()
    login_audit_events = (
        await db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.timestamp >= start,
                AuditLog.timestamp <= end,
                AuditLog.action.in_(["login", "login_failed", "oidc_login"]),
            )
        )
    ).scalar_one()
    role_change_events = (
        await db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.timestamp >= start,
                AuditLog.action.in_(["user_role_update", "user_provisioned", "user_invited"]),
            )
        )
    ).scalar_one()
    config_change_events = (
        await db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.timestamp >= start,
                AuditLog.action.in_([
                    "playbook_created",
                    "playbook_deleted",
                    "building_block_created",
                    "alert_rule_update",
                ]),
            )
        )
    ).scalar_one()
    user_provision_events = (
        await db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.timestamp >= start,
                AuditLog.action.in_(["user_provisioned", "user_invited", "user_invite_accepted"]),
            )
        )
    ).scalar_one()

    role_count = (await db.execute(select(func.count()).select_from(Role))).scalar_one()
    active_users = (
        await db.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))
    ).scalar_one()

    roles = {r.name: r.id for r in (await db.execute(select(Role))).scalars().all()}
    admin_users = 0
    analyst_users = 0
    if roles.get("admin"):
        admin_users = (
            await db.execute(select(func.count()).select_from(User).where(User.role_id == roles["admin"], User.is_active.is_(True)))
        ).scalar_one()
    if roles.get("analyst"):
        analyst_users = (
            await db.execute(select(func.count()).select_from(User).where(User.role_id == roles["analyst"], User.is_active.is_(True)))
        ).scalar_one()

    hosts_total = (await db.execute(select(func.count()).select_from(Host))).scalar_one()
    hosts_monitored = (
        await db.execute(select(func.count()).select_from(Host).where(Host.api_key_hash.isnot(None)))
    ).scalar_one()
    agent_coverage_pct = round(100 * hosts_monitored / hosts_total, 1) if hosts_total else 0

    events_period = (
        await db.execute(select(func.count()).select_from(Event).where(Event.timestamp >= start, Event.timestamp <= end))
    ).scalar_one()
    failed_login_events = (
        await db.execute(
            select(func.count()).select_from(Event).where(
                Event.timestamp >= start,
                Event.timestamp <= end,
                Event.event_type == "ssh_login_failure",
            )
        )
    ).scalar_one()

    alerts_created_period = (
        await db.execute(select(func.count()).select_from(Alert).where(Alert.created_at >= start, Alert.created_at <= end))
    ).scalar_one()
    alerts_resolved_period = (
        await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.created_at >= start,
                Alert.created_at <= end,
                Alert.status.in_(["resolved", "closed"]),
            )
        )
    ).scalar_one()
    resolution_rate = round(100 * alerts_resolved_period / alerts_created_period, 1) if alerts_created_period else 100.0

    critical_high_open = (
        await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.status.in_(["open", "investigating"]),
                Alert.severity.in_(["critical", "high"]),
            )
        )
    ).scalar_one()

    detection_rules_enabled = (
        await db.execute(select(func.count()).select_from(AlertRule).where(AlertRule.enabled.is_(True)))
    ).scalar_one()
    incidents_open = (
        await db.execute(
            select(func.count()).select_from(Incident).where(Incident.status.in_(["open", "investigating"]))
        )
    ).scalar_one()
    incidents_created_period = (
        await db.execute(
            select(func.count()).select_from(Incident).where(Incident.created_at >= start, Incident.created_at <= end)
        )
    ).scalar_one()
    offenses_open = (
        await db.execute(
            select(func.count()).select_from(Offense).where(Offense.status.in_(["open", "investigating"]))
        )
    ).scalar_one()
    ueba_open = (
        await db.execute(select(func.count()).select_from(UebaAnomaly).where(UebaAnomaly.status == "open"))
    ).scalar_one()
    playbooks_count = (await db.execute(select(func.count()).select_from(Playbook))).scalar_one()

    from app.models.threat_score import HostThreatScore

    hosts_scored = (await db.execute(select(func.count()).select_from(HostThreatScore))).scalar_one()

    return {
        "audit_events_period": audit_events_period,
        "login_audit_events": login_audit_events,
        "role_change_events": role_change_events,
        "config_change_events": config_change_events,
        "user_provision_events": user_provision_events,
        "role_count": role_count,
        "active_users": active_users,
        "admin_users": admin_users,
        "analyst_users": analyst_users,
        "oidc_enabled": settings.oidc_enabled,
        "oidc_auto_provision": settings.oidc_auto_provision,
        "lockout_enabled": settings.account_lockout_attempts > 0,
        "hosts_total": hosts_total,
        "hosts_monitored": hosts_monitored,
        "agent_coverage_pct": agent_coverage_pct,
        "events_period": events_period,
        "failed_login_events": failed_login_events,
        "alerts_created_period": alerts_created_period,
        "alerts_resolved_period": alerts_resolved_period,
        "resolution_rate": resolution_rate,
        "critical_high_open": critical_high_open,
        "detection_rules_enabled": detection_rules_enabled,
        "incidents_open": incidents_open,
        "incidents_created_period": incidents_created_period,
        "offenses_open": offenses_open,
        "ueba_enabled": settings.ueba_enabled,
        "ueba_open": ueba_open,
        "playbooks_count": playbooks_count,
        "hosts_scored": hosts_scored,
        "retention_days": settings.retention_days,
    }


async def build_compliance_report(db: AsyncSession, framework_id: str, report_type: str) -> dict[str, Any]:
    if framework_id not in COMPLIANCE_FRAMEWORKS:
        raise ValueError(f"Unknown framework: {framework_id}")
    start, end = period_bounds(report_type)
    evidence = await gather_compliance_evidence(db, start, end)
    controls = evaluate_framework(framework_id, evidence)

    pass_count = sum(1 for c in controls if c["status"] == "pass")
    partial_count = sum(1 for c in controls if c["status"] == "partial")
    fail_count = sum(1 for c in controls if c["status"] == "fail")

    fw = COMPLIANCE_FRAMEWORKS[framework_id]
    return {
        "framework_id": framework_id,
        "framework_name": fw["name"],
        "report_type": report_type,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_controls": len(controls),
            "pass": pass_count,
            "partial": partial_count,
            "fail": fail_count,
            "compliance_score": round(100 * (pass_count + 0.5 * partial_count) / max(len(controls), 1), 1),
        },
        "evidence": evidence,
        "controls": controls,
    }


def export_compliance_pdf(data: dict[str, Any], filename: str) -> Response:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise RuntimeError("reportlab is required for PDF export") from exc

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#0f2744"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#1e3a5f"), spaceBefore=10, spaceAfter=4)
    body = styles["Normal"]

    summary = data.get("summary") or {}
    story: list[Any] = [
        Paragraph(f"{data.get('framework_name', 'Compliance')} Report", title_style),
        Paragraph(
            f"Period: {_fmt(data.get('period_start'))} — {_fmt(data.get('period_end'))}<br/>"
            f"Score: <b>{summary.get('compliance_score', 0)}%</b> "
            f"({summary.get('pass', 0)} pass · {summary.get('partial', 0)} partial · {summary.get('fail', 0)} fail)",
            body,
        ),
        Spacer(1, 12),
    ]

    rows = [["Control", "Title", "Status"]]
    for c in data.get("controls") or []:
        rows.append([c["id"], c["title"][:40], c["status"].upper()])
    table = Table(rows, colWidths=[1 * inch, 3.5 * inch, 1 * inch], repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ])
    )
    story.append(table)

    for c in data.get("controls") or []:
        story.append(Paragraph(f"{c['id']} — {c['title']}", h2))
        story.append(Paragraph(f"<i>{c['requirement']}</i>", body))
        story.append(Paragraph(f"Status: <b>{c['status'].upper()}</b>", body))
        for finding in c.get("findings") or []:
            story.append(Paragraph(f"• {finding}", body))
        if c.get("recommendation"):
            story.append(Paragraph(f"<font color='#b45309'>Action: {c['recommendation']}</font>", body))
        story.append(Spacer(1, 6))

    doc.build(story)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _fmt(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return str(value)[:19]


def get_templates() -> list[dict[str, str]]:
    return list_frameworks()
