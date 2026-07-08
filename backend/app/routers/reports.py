import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.alert import Alert
from app.models.event import Event
from app.models.host import Host
from app.models.siem import GeneratedReport
from app.models.threat_score import HostThreatScore
from app.models.user import User
from app.services import siem_analytics
from app.services.compliance_report import build_compliance_report, export_compliance_pdf, get_templates
from app.services.executive_report import build_executive_report_data, export_executive_pdf, period_bounds
from app.services.export_service import export_csv
from app.utils.query import resolve_time_range

router = APIRouter(prefix="/reports", tags=["reports"])


def _period_bounds(report_type: str) -> tuple[datetime, datetime]:
    return period_bounds(report_type)


async def _build_report_data(db: AsyncSession, report_type: str) -> dict:
    start, end = _period_bounds(report_type)
    tr = resolve_time_range(None, start, end)

    total_events = (
        await db.execute(select(func.count()).select_from(Event).where(Event.timestamp >= start))
    ).scalar_one()
    total_alerts = (
        await db.execute(select(func.count()).select_from(Alert).where(Alert.created_at >= start))
    ).scalar_one()
    top_hosts = await siem_analytics.top_risky_hosts(db, 10)
    failed = await siem_analytics.failed_login_analytics(db, tr)
    mitre = await siem_analytics.mitre_stats(db, tr)
    timelines = await siem_analytics.attack_timeline_list(db, tr)

    return {
        "report_type": report_type,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "total_events": total_events,
        "total_alerts": total_alerts,
        "top_hosts": top_hosts,
        "failed_logins": failed.get("top_attacking_ips", []),
        "mitre_techniques": mitre.get("techniques", [])[:20],
        "attack_timelines": timelines[:10],
    }


@router.get("/summary")
async def report_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    format: str = Query("json"),
):
    hosts = (await db.execute(select(func.count()).select_from(Host))).scalar_one()
    alerts = (await db.execute(select(func.count()).select_from(Alert).where(Alert.status == "open"))).scalar_one()
    scores = list((await db.execute(select(HostThreatScore).order_by(HostThreatScore.score.desc()))).scalars().all())
    data = {"total_hosts": hosts, "open_alerts": alerts, "threat_scores": [{"host_id": str(s.host_id), "score": s.score} for s in scores]}
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["host_id", "threat_score"])
        for s in scores:
            w.writerow([str(s.host_id), s.score])
        return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=report.csv"})
    return data


@router.get("/executive")
async def executive_report(
    report_type: str = Query("weekly", pattern="^(daily|weekly|monthly)$"),
    format: str = Query("pdf", pattern="^(json|pdf)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Executive-ready PDF with KPIs, MITRE, UEBA, and recommendations."""
    data = await build_executive_report_data(db, report_type)
    start, end = _period_bounds(report_type)

    report_row = GeneratedReport(
        user_id=user.id,
        report_type=f"executive_{report_type}",
        period_start=start,
        period_end=end,
        format=format,
        summary=data,
    )
    db.add(report_row)
    await db.commit()

    filename = f"securi_executive_{report_type}.pdf"
    if format == "pdf":
        return export_executive_pdf(data, filename)
    return data


@router.get("/compliance/templates")
async def compliance_templates(user: User = Depends(get_current_user)):
    return get_templates()


@router.get("/compliance")
async def compliance_report(
    framework: str = Query("soc2", pattern="^(soc2|iso27001)$"),
    report_type: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    format: str = Query("pdf", pattern="^(json|pdf)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """SOC 2 / ISO 27001 control assessment with platform evidence."""
    try:
        data = await build_compliance_report(db, framework, report_type)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start, end = _period_bounds(report_type)
    report_type_value = f"compliance_{framework}_{report_type}"
    report_row = GeneratedReport(
        user_id=user.id,
        report_type=report_type_value,
        period_start=start,
        period_end=end,
        format=format,
        summary=data,
    )
    db.add(report_row)
    await db.commit()

    if format == "pdf":
        return export_compliance_pdf(data, f"securi_compliance_{framework}_{report_type}.pdf")
    return data


@router.get("/generate")
async def generate_report(
    report_type: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    format: str = Query("json", pattern="^(json|csv|pdf)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await _build_report_data(db, report_type)
    start, end = _period_bounds(report_type)

    report_row = GeneratedReport(
        user_id=user.id,
        report_type=report_type,
        period_start=start,
        period_end=end,
        format=format,
        summary=data,
    )
    db.add(report_row)
    await db.commit()

    filename = f"securi_{report_type}_report"
    if format == "csv":
        rows = [
            {"metric": "total_events", "value": data["total_events"]},
            {"metric": "total_alerts", "value": data["total_alerts"]},
        ]
        for h in data["top_hosts"]:
            rows.append({"metric": f"risk_{h['host_name']}", "value": h["risk_score"]})
        return export_csv(rows, f"{filename}.csv")
    if format == "pdf":
        exec_data = await build_executive_report_data(db, report_type)
        return export_executive_pdf(exec_data, f"{filename}.pdf")
    return data
