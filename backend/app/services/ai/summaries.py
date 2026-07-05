"""Alert and offense summary generation."""

from app.services.ai.context import load_alert_context, load_offense_context
from app.services.ai.llm import call_llm, resolve_provider
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


def _severity_action(severity: str) -> str:
    return {
        "critical": "Treat as P1 — escalate immediately and contain affected host if confirmed.",
        "high": "Prioritize within SLA — assign analyst and begin investigation within 1 hour.",
        "medium": "Review within business hours; correlate with nearby events.",
        "low": "Monitor and batch with similar alerts unless pattern emerges.",
    }.get(severity, "Review and triage based on host criticality.")


def _investigation_steps_for_alert(ctx: dict) -> list[str]:
    alert = ctx["alert"]
    host = ctx["host"]
    steps = [
        f"Confirm alert scope on host **{host['name']}** ({host.get('status', 'unknown')} status).",
        "Review related events ±30 minutes around detection time in the investigation pane.",
        "Check host threat score and any active attack timelines.",
    ]
    if alert.get("mitre_technique_id"):
        steps.append(f"Map behavior to MITRE {alert['mitre_technique_id']} and check for lateral movement.")
    if host.get("ip_address"):
        steps.append(f"Run IOC lookup on {host['ip_address']} and linked artifacts.")
    steps.append("Document findings and set alert status to investigating or resolved.")
    return steps


def _local_alert_summary(ctx: dict) -> dict:
    alert = ctx["alert"]
    host = ctx["host"]
    events = ctx.get("recent_events", [])

    event_summary = ""
    if events:
        types = ", ".join(dict.fromkeys(e["event_type"] for e in events[:3]))
        event_summary = f" Recent activity includes: {types}."

    summary = (
        f"**{alert['severity'].upper()}** alert on host **{host['name']}**: "
        f"{alert['title']}.{event_summary} "
        f"Status: {alert['status']}"
        + (f", confidence {alert['confidence']:.0f}%" if alert.get("confidence") else "")
        + "."
    )

    return {
        "summary": summary,
        "investigation_steps": _investigation_steps_for_alert(ctx),
        "recommended_actions": [
            _severity_action(alert["severity"]),
            "Promote to offense if multiple correlated alerts appear on this host.",
            "Check simulation tag if this originated from Attack Simulation lab.",
        ],
    }


async def generate_alert_summary(db: AsyncSession, alert_id: UUID) -> dict | None:
    ctx = await load_alert_context(db, alert_id)
    if not ctx:
        return None

    local = _local_alert_summary(ctx)
    provider = resolve_provider()

    if provider != "local":
        prompt = (
            f"Alert: {ctx['alert']}\nHost: {ctx['host']}\nRecent events: {ctx.get('recent_events', [])}\n"
            "Write a 2-3 sentence analyst summary and bullet investigation steps."
        )
        llm_text = await call_llm(
            "You are a SOC analyst assistant. Be concise and actionable.",
            prompt,
        )
        if llm_text:
            return {
                "alert_id": str(alert_id),
                "summary": llm_text,
                "investigation_steps": local["investigation_steps"],
                "recommended_actions": local["recommended_actions"],
                "provider": provider,
            }

    return {
        "alert_id": str(alert_id),
        **local,
        "provider": "local",
    }


def _local_offense_brief(ctx: dict) -> dict:
    offense = ctx["offense"]
    host = ctx["host"]
    alerts = ctx.get("linked_alert_titles", [])
    events = ctx.get("linked_event_types", [])

    brief_parts = [
        f"Offense #{offense['offense_number']} (**{offense['risk_level']}** risk) on **{host['name']}**: "
        f"{offense['title']}.",
        f"Correlates {offense['event_count']} events and {offense['alert_count']} alerts.",
    ]
    if alerts:
        brief_parts.append(f"Key alerts: {', '.join(alerts[:3])}.")
    if events:
        brief_parts.append(f"Event types involved: {', '.join(events[:5])}.")

    findings = []
    if offense.get("related_hosts"):
        findings.append(f"Related hosts: {', '.join(str(h) for h in offense['related_hosts'][:5])}")
    if offense.get("related_users"):
        findings.append(f"Related users: {', '.join(str(u) for u in offense['related_users'][:5])}")
    if offense.get("timeline"):
        findings.append(f"Timeline has {len(offense['timeline'])} correlated stages")
    if not findings:
        findings.append("Review linked alerts and events in the offense detail view")

    actions = [
        "Assign primary analyst and set offense status to investigating.",
        "Review MITRE mapping and attack timeline for this host.",
        "Promote to incident if business impact or data exposure is confirmed.",
    ]
    if offense["risk_level"] in ("critical", "high"):
        actions.insert(0, "Escalate to incident response — high/critical offense.")

    return {
        "brief": " ".join(brief_parts),
        "key_findings": findings,
        "recommended_actions": actions,
    }


async def generate_offense_brief(db: AsyncSession, offense_id: UUID) -> dict | None:
    ctx = await load_offense_context(db, offense_id)
    if not ctx:
        return None

    local = _local_offense_brief(ctx)
    provider = resolve_provider()

    if provider != "local":
        prompt = f"Offense context: {ctx}\nWrite a plain-English 3-4 sentence threat brief for an analyst."
        llm_text = await call_llm(
            "You are a SOC threat intelligence analyst. Write clear, factual briefs.",
            prompt,
        )
        if llm_text:
            return {
                "offense_id": str(offense_id),
                "brief": llm_text,
                "key_findings": local["key_findings"],
                "recommended_actions": local["recommended_actions"],
                "provider": provider,
            }

    return {
        "offense_id": str(offense_id),
        **local,
        "provider": "local",
    }
