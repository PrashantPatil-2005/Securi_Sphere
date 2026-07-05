"""Context-aware security assistant — local templates + optional LLM."""

import re

from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.services.ai.context import load_alert_context, load_offense_context
from app.services.ai.llm import call_llm, resolve_provider
from app.services.ai.nl_search import nl_to_siem_query_local


def _format_context_block(ctx: dict | None, siem_query: str | None) -> str:
    lines: list[str] = []
    if ctx:
        if ctx["type"] == "alert":
            a, h = ctx["alert"], ctx["host"]
            lines.append(f"Alert: [{a['severity']}] {a['title']} (status: {a['status']})")
            lines.append(f"Host: {h['name']} ({h.get('status')})")
            if a.get("description"):
                lines.append(f"Description: {a['description'][:300]}")
            if a.get("mitre_technique_id"):
                lines.append(f"MITRE: {a['mitre_technique_id']}")
        elif ctx["type"] == "offense":
            o, h = ctx["offense"], ctx["host"]
            lines.append(f"Offense #{o['offense_number']}: {o['title']} ({o['risk_level']})")
            lines.append(f"Host: {h['name']}, events: {o['event_count']}, alerts: {o['alert_count']}")
    if siem_query:
        lines.append(f"Active SIEM query: {siem_query}")
    return "\n".join(lines)


def _local_chat_reply(message: str, ctx: dict | None, siem_query: str | None) -> tuple[str, list[str]]:
    lower = message.lower().strip()
    suggestions: list[str] = []

    if ctx and ctx["type"] == "alert":
        alert = ctx["alert"]
        host = ctx["host"]

        if (
            any(w in lower for w in ("step", "investigate", "how", "next", "do"))
            and ("investig" in lower or "step" in lower)
        ):
            steps = [
                f"1. Set alert status to **investigating** and assign an analyst.",
                f"2. Review events ±30 min on **{host['name']}** in the investigation pane.",
                "3. Check attack timelines and MITRE mapping for this host.",
                "4. Run IOC lookup on IPs/domains from related events.",
                "5. Resolve or promote to offense if pattern persists.",
            ]
            return "**Investigation playbook:**\n\n" + "\n".join(steps), [
                "Summarize this alert",
                "What MITRE techniques apply?",
            ]

        if any(w in lower for w in ("explain", "what", "why", "mean", "summary", "about")) and "step" not in lower:
            reply = (
                f"This is a **{alert['severity']}** alert: **{alert['title']}** on host **{host['name']}**. "
                f"Current status is **{alert['status']}**."
            )
            if alert.get("description"):
                reply += f" {alert['description']}"
            if alert.get("mitre_technique_id"):
                reply += f" Mapped to MITRE technique {alert['mitre_technique_id']}."
            suggestions = [
                "What investigation steps should I take?",
                "Show related events",
                "Is this host at high risk?",
            ]
            return reply, suggestions

        if any(w in lower for w in ("risk", "score", "danger")):
            score = host.get("risk_score")
            if score is not None:
                level = "high" if score > 70 else "elevated" if score > 40 else "moderate"
                return (
                    f"Host **{host['name']}** has threat score **{score}** ({level}). "
                    f"Alert severity is **{alert['severity']}**.",
                    ["What should I do first?", "Show investigation steps"],
                )
            return f"No threat score yet for **{host['name']}**. Review recent events manually.", []

    if ctx and ctx["type"] == "offense":
        offense = ctx["offense"]
        if any(w in lower for w in ("brief", "summary", "explain", "what", "tell")):
            return (
                f"Offense **#{offense['offense_number']}** ({offense['risk_level']}): {offense['title']}. "
                f"Includes {offense['event_count']} events and {offense['alert_count']} alerts. "
                f"Status: {offense['status']}.",
                ["Recommend next actions", "Should I promote to incident?"],
            )
        if any(w in lower for w in ("incident", "promote", "escalate")):
            if offense["risk_level"] in ("critical", "high"):
                return (
                    "**Yes — consider promoting to incident.** "
                    f"This is a {offense['risk_level']}-risk offense with {offense['alert_count']} correlated alerts.",
                    ["What are the key findings?"],
                )
            return (
                "Promotion is optional for medium/low offenses unless business impact is confirmed. "
                "Review linked alerts first.",
                ["Summarize this offense"],
            )

    if any(w in lower for w in ("siem", "syntax", "language", "field")) and "search" not in lower[:20]:
        return (
            "**SIEM query syntax:** use `field:value` tokens joined by spaces.\n\n"
            "- `host:web01 severity:critical`\n"
            "- `event_type:ssh_login_failure date:24h`\n"
            "- `username:root source_ip:10.0.0.5`\n\n"
            "Date presets: `15m`, `1h`, `24h`, `7d`. Try natural language on the Search page.",
            ["Show failed logins from last hour", "Find critical alerts"],
        )

    if any(w in lower for w in ("search", "find", "show me")) or (
        "query" in lower and "syntax" not in lower and "siem" not in lower
    ):
        siem_q, expl, _ = nl_to_siem_query_local(message)
        return (
            f"I'd search with: `{siem_q}`\n\n{expl}. "
            "Open **Search → SIEM** and paste this query, or use the NL search box.",
            ["Run simulation to generate test data", "Explain SIEM query syntax"],
        )

    if any(w in lower for w in ("simulation", "demo", "lab", "test")):
        return (
            "Use **Attack Simulation** (Management → Simulation): pick a host, run `brute_force` or "
            "`multi_stage_attack`, then triage alerts and offenses. Great for portfolio demos.",
            ["What investigation steps for alerts?", "Explain offense workflow"],
        )

    if any(w in lower for w in ("mitre", "attack", "technique", "tactic")):
        return (
            "Open **MITRE ATT&CK** to see technique coverage from your detections. "
            "Alerts with MITRE IDs appear in the investigation pane.",
            ["Explain this alert", "Show investigation steps"],
        )

    if any(w in lower for w in ("hello", "hi", "help")):
        return (
            "I'm the SecuriSphere AI assistant. I can explain alerts, suggest investigation steps, "
            "convert natural language to SIEM queries, and summarize offenses. "
            "Open me from an alert investigation or ask anything about your SOC workflow.",
            [
                "Explain this alert",
                "What investigation steps should I take?",
                "Show failed logins from last hour",
            ],
        )

    # Generic fallback with context
    if ctx:
        block = _format_context_block(ctx, siem_query)
        return (
            f"I can help investigate the current context:\n\n{block}\n\n"
            "Try asking: *explain this alert*, *investigation steps*, or *should I escalate?*",
            ["Explain this alert", "Investigation steps", "Recommend next actions"],
        )

    return (
        "I can help with alert triage, offense summaries, SIEM queries, and SOC workflow guidance. "
        "Select an alert and use **Ask AI**, or ask about simulation, MITRE, or search syntax.",
        [
            "How do I run attack simulation?",
            "Show failed logins from last hour",
            "Explain SIEM query syntax",
        ],
    )


async def chat(
    db: AsyncSession,
    message: str,
    alert_id: UUID | None = None,
    offense_id: UUID | None = None,
    siem_query: str | None = None,
) -> dict:
    ctx = None
    if alert_id:
        ctx = await load_alert_context(db, alert_id)
    elif offense_id:
        ctx = await load_offense_context(db, offense_id)

    provider = resolve_provider()
    context_block = _format_context_block(ctx, siem_query)

    if provider != "local":
        system = (
            "You are SecuriSphere SOC assistant. Answer concisely in markdown. "
            "Use only provided context; do not invent incidents. "
            "Suggest practical next steps for analysts."
        )
        user_prompt = f"Context:\n{context_block}\n\nAnalyst question: {message}"
        llm_reply = await call_llm(system, user_prompt)
        if llm_reply:
            _, suggestions = _local_chat_reply(message, ctx, siem_query)
            return {"reply": llm_reply, "provider": provider, "suggestions": suggestions[:4]}

    reply, suggestions = _local_chat_reply(message, ctx, siem_query)
    # Strip accidental markdown bold markers duplication for plain responses
    reply = re.sub(r"\*\*([^*]+)\*\*", r"**\1**", reply)
    return {"reply": reply, "provider": "local", "suggestions": suggestions[:4]}
