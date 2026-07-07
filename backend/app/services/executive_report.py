"""Executive security report — data assembly and branded PDF export."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.brand import PRODUCT_NAME
from app.models.alert import Alert
from app.models.incident import Incident
from app.models.siem import Offense
from app.models.ueba import UebaAnomaly
from app.services import siem_analytics
from app.utils.query import resolve_time_range


def period_bounds(report_type: str) -> tuple[datetime, datetime]:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    if report_type == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif report_type == "weekly":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


async def build_executive_report_data(db: AsyncSession, report_type: str) -> dict[str, Any]:
    start, end = period_bounds(report_type)
    tr = resolve_time_range(None, start, end)

    summary = await siem_analytics.executive_summary(db, tr)
    severity = await siem_analytics.severity_distribution(db, tr)
    top_hosts = await siem_analytics.top_risky_hosts(db, 10)
    mitre = await siem_analytics.mitre_stats(db, tr)
    failed = await siem_analytics.failed_login_analytics(db, tr)
    timelines = await siem_analytics.attack_timeline_list(db, tr)

    by_ip = failed.get("by_source_ip") or failed.get("top_attacking_ips") or []
    total_failures = sum(item.get("count", 0) for item in by_ip)
    if not total_failures and failed.get("over_time"):
        total_failures = sum(p.get("count", 0) for p in failed["over_time"])

    open_offenses = (
        await db.execute(
            select(func.count()).select_from(Offense).where(Offense.status.in_(["open", "investigating"]))
        )
    ).scalar_one()
    period_offenses = (
        await db.execute(
            select(func.count()).select_from(Offense).where(Offense.created_at >= start, Offense.created_at <= end)
        )
    ).scalar_one()
    open_incidents = (
        await db.execute(
            select(func.count()).select_from(Incident).where(Incident.status.in_(["open", "investigating"]))
        )
    ).scalar_one()
    ueba_open = (
        await db.execute(select(func.count()).select_from(UebaAnomaly).where(UebaAnomaly.status == "open"))
    ).scalar_one()

    resolved_alerts = (
        await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.created_at >= start,
                Alert.created_at <= end,
                Alert.status.in_(["resolved", "closed"]),
            )
        )
    ).scalar_one()

    recommendations = _build_recommendations(
        summary=summary,
        open_offenses=open_offenses,
        ueba_open=ueba_open,
        failed=failed,
    )

    return {
        "report_type": report_type,
        "title": f"{PRODUCT_NAME} Executive Security Report — {report_type.title()}",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": summary,
        "severity_distribution": severity.get("distribution", []),
        "top_risky_hosts": top_hosts,
        "mitre_techniques": mitre.get("techniques", [])[:15],
        "failed_logins": {
            "total": total_failures,
            "unique_ips": len(by_ip),
            "top_ips": (failed.get("top_attacking_ips") or by_ip)[:8],
        },
        "attack_timelines": timelines[:5],
        "open_offenses": open_offenses,
        "period_offenses": period_offenses,
        "open_incidents": open_incidents,
        "ueba_open_anomalies": ueba_open,
        "resolved_alerts_period": resolved_alerts,
        "recommendations": recommendations,
    }


def _build_recommendations(
    *,
    summary: dict,
    open_offenses: int,
    ueba_open: int,
    failed: dict,
) -> list[str]:
    recs: list[str] = []
    if summary.get("critical_alerts", 0) > 0:
        recs.append(
            f"Triage {summary['critical_alerts']} critical alert(s) immediately and assign incident owners."
        )
    if open_offenses > 0:
        recs.append(f"Review {open_offenses} open offense(s) and promote high-risk items to formal incidents.")
    if ueba_open > 0:
        recs.append(f"Investigate {ueba_open} UEBA baseline anomaly(ies) on the Analytics dashboard.")
    if failed.get("total_failures", 0) > 20:
        recs.append("Elevated failed login volume — enforce MFA and review exposed SSH/RDP surfaces.")
    if summary.get("average_risk_score", 0) > 60:
        recs.append("Fleet average risk score is elevated; prioritize patching and host hardening on top risky hosts.")
    online = summary.get("online_hosts", 0)
    total = summary.get("total_hosts", 0)
    if total and online / max(total, 1) < 0.8:
        recs.append("More than 20% of hosts are offline or degraded — verify agent connectivity.")
    if not recs:
        recs.append("Security posture is within normal parameters for the period. Continue monitoring and weekly reviews.")
    return recs


def export_executive_pdf(data: dict[str, Any], filename: str) -> Response:
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
    title_style = ParagraphStyle(
        "ExecTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#0f2744"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ExecSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#5a6a7a"),
        spaceAfter=14,
    )
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#1e3a5f"), spaceBefore=12, spaceAfter=6)
    body = styles["Normal"]

    story: list[Any] = []
    story.append(Paragraph(data.get("title", "Executive Security Report"), title_style))
    story.append(
        Paragraph(
            f"Period: {_fmt_dt(data.get('period_start'))} — {_fmt_dt(data.get('period_end'))}<br/>"
            f"Generated: {_fmt_dt(data.get('generated_at'))}",
            subtitle_style,
        )
    )

    summary = data.get("executive_summary") or {}
    kpi_rows = [
        ["Metric", "Value"],
        ["Total hosts", str(summary.get("total_hosts", 0))],
        ["Online hosts", str(summary.get("online_hosts", 0))],
        ["Active alerts", str(summary.get("active_alerts", 0))],
        ["Critical alerts", str(summary.get("critical_alerts", 0))],
        ["Events (period)", str(summary.get("total_events", 0))],
        ["Alerts (period)", str(summary.get("period_alerts", 0))],
        ["Avg risk score", str(summary.get("average_risk_score", 0))],
        ["Open offenses", str(data.get("open_offenses", 0))],
        ["Open incidents", str(data.get("open_incidents", 0))],
        ["UEBA anomalies", str(data.get("ueba_open_anomalies", 0))],
    ]
    story.append(Paragraph("Executive summary", h2))
    story.append(_styled_table(kpi_rows, col_widths=[3.2 * inch, 2 * inch]))

    sev = data.get("severity_distribution") or []
    if sev:
        story.append(Paragraph("Alert severity (period)", h2))
        sev_rows = [["Severity", "Count", "%"]] + [
            [s.get("severity", ""), str(s.get("count", 0)), f"{s.get('percentage', 0)}%"] for s in sev
        ]
        story.append(_styled_table(sev_rows))

    hosts = data.get("top_risky_hosts") or []
    if hosts:
        story.append(Paragraph("Top risky hosts", h2))
        host_rows = [["Host", "Risk", "Alerts"]] + [
            [h.get("host_name", ""), str(h.get("risk_score", 0)), str(h.get("active_alerts", 0))] for h in hosts[:10]
        ]
        story.append(_styled_table(host_rows))

    techniques = data.get("mitre_techniques") or []
    if techniques:
        story.append(Paragraph("MITRE ATT&amp;CK highlights", h2))
        mitre_rows = [["Technique", "Tactic", "Events"]] + [
            [t.get("technique_id", ""), t.get("tactic", ""), str(t.get("count", 0))] for t in techniques[:12]
        ]
        story.append(_styled_table(mitre_rows))

    failed = data.get("failed_logins") or {}
    story.append(Paragraph("Authentication threats", h2))
    story.append(
        Paragraph(
            f"Failed logins: <b>{failed.get('total', 0)}</b> from <b>{failed.get('unique_ips', 0)}</b> unique source IP(s).",
            body,
        )
    )
    top_ips = failed.get("top_ips") or []
    if top_ips:
        ip_rows = [["Source IP", "Failures"]] + [
            [ip.get("source_ip", ip.get("ip", "")), str(ip.get("count", ip.get("failed_attempts", 0)))]
            for ip in top_ips[:8]
        ]
        story.append(Spacer(1, 6))
        story.append(_styled_table(ip_rows))

    recs = data.get("recommendations") or []
    if recs:
        story.append(Paragraph("Recommendations", h2))
        for rec in recs:
            story.append(Paragraph(f"• {rec}", body))
            story.append(Spacer(1, 4))

    story.append(Spacer(1, 16))
    story.append(Paragraph(f"{PRODUCT_NAME} SIEM — Confidential", subtitle_style))

    doc.build(story)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _styled_table(rows: list[list[str]], col_widths: list[float] | None = None):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c5d0dc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _fmt_dt(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return str(value)[:19]
