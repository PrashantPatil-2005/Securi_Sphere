import csv
import io
from datetime import datetime, timedelta, timezone

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
from app.services.export_service import export_csv, export_pdf
from app.utils.query import resolve_time_range

router = APIRouter(prefix="/reports", tags=["reports"])


def _period_bounds(report_type: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if report_type == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif report_type == "weekly":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


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

    filename = f"securisphere_{report_type}_report"
    if format == "csv":
        rows = [
            {"metric": "total_events", "value": data["total_events"]},
            {"metric": "total_alerts", "value": data["total_alerts"]},
        ]
        for h in data["top_hosts"]:
            rows.append({"metric": f"risk_{h['host_name']}", "value": h["risk_score"]})
        return export_csv(rows, f"{filename}.csv")
    if format == "pdf":
        rows = [
            {"metric": "Total Events", "value": data["total_events"]},
            {"metric": "Total Alerts", "value": data["total_alerts"]},
        ]
        for h in data["top_hosts"][:10]:
            rows.append({"Host": h["host_name"], "Risk Score": h["risk_score"], "Alerts": h["active_alerts"]})
        return export_pdf(rows, f"SecuriSphere {report_type.title()} Security Report", f"{filename}.pdf")
    return data
