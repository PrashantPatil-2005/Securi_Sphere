"""Rule-based natural language to SIEM query conversion."""

import re

from app.brand import PRODUCT_NAME
from app.services.ai.llm import call_llm, resolve_provider

# (pattern, siem_query_template or callable)
_TIME_PATTERNS = [
    (r"\b(last|past)\s+(15\s*min(ute)?s?|quarter\s+hour)\b", "date:15m"),
    (r"\b(last|past)\s+(30\s*min(ute)?s?|half\s+hour)\b", "date:30m"),
    (r"\b(last|past)\s+hour\b", "date:1h"),
    (r"\b(last|past)\s+(6\s*hours?|six\s+hours?)\b", "date:6h"),
    (r"\b(last|past)\s+(12\s*hours?|half\s+day)\b", "date:12h"),
    (r"\b(last|past)\s+(24\s*hours?|day|1\s+day)\b", "date:24h"),
    (r"\b(last|past)\s+(7\s*days?|week)\b", "date:7d"),
    (r"\b(last|past)\s+(30\s*days?|month)\b", "date:30d"),
]

_INTENT_PATTERNS: list[tuple[str, str]] = [
    (r"\bfailed\s+(login|logins|logon|authentication|auth)\b", "event_type:ssh_login_failure"),
    (r"\bssh\s+(fail|failure|brute)\b", "event_type:ssh_login_failure"),
    (r"\bbrute\s*force\b", "event_type:ssh_login_failure"),
    (r"\bsudo\b|\belevated\s+privilege\b|\bprivilege\s+escalation\b", "event_type:sudo_usage"),
    (r"\bport\s+scan\b|\bscanning\b", "event_type:port_scan"),
    (r"\bcritical\s+alerts?\b", "severity:critical status:open"),
    (r"\bhigh\s+severity\s+alerts?\b", "severity:high status:open"),
    (r"\bopen\s+alerts?\b", "status:open"),
    (r"\bresolved\s+alerts?\b", "status:resolved"),
    (r"\bcritical\s+events?\b", "severity:critical"),
    (r"\bhigh\s+severity\s+events?\b", "severity:high"),
    (r"\bnetwork\s+(flow|traffic|connection)\b", "event_type:network_flow"),
    (r"\bmalware\b|\bvirus\b", "event_type:malware_detected"),
    (r"\bfile\s+(change|modification|integrity)\b", "event_type:file_integrity"),
]

_HOST_NAME_RE = re.compile(r"\bhost\s+([a-zA-Z0-9._-]+)\b", re.I)
_HOST_FROM_RE = re.compile(r"\b(?:on|from|for)\s+([a-zA-Z0-9._-]+)\b", re.I)
_USER_RE = re.compile(r"\b(?:user|username)\s+([a-zA-Z0-9._-]+)\b", re.I)
_IP_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


def nl_to_siem_query_local(text: str) -> tuple[str, str, str]:
    """Return (siem_query, explanation, confidence)."""
    original = text.strip()
    lower = original.lower()
    parts: list[str] = []
    explanations: list[str] = []

    for pattern, siem_part in _INTENT_PATTERNS:
        if re.search(pattern, lower):
            if siem_part not in parts:
                parts.append(siem_part)
                explanations.append(_explain_part(siem_part))

    for pattern, date_part in _TIME_PATTERNS:
        if re.search(pattern, lower):
            if date_part not in parts:
                parts.append(date_part)
                explanations.append("Time range applied from your phrase")
            break

    host_match = _HOST_NAME_RE.search(original)
    if host_match:
        host_name = host_match.group(1)
    else:
        host_match = _HOST_FROM_RE.search(original)
        host_name = host_match.group(1) if host_match else None
    if host_name and host_name.lower() not in ("the", "a", "an", "last", "past", "show", "all", "host"):
        parts.append(f"host:{host_name}")
        explanations.append(f"Filtered to host {host_name}")

    user_match = _USER_RE.search(original)
    if user_match:
        username = user_match.group(1)
        parts.append(f"username:{username}")
        explanations.append(f"Filtered to user {username}")

    ip_match = _IP_RE.search(original)
    if ip_match:
        ip = ip_match.group(1)
        parts.append(f"source_ip:{ip}")
        explanations.append(f"Filtered to source IP {ip}")

    if not parts:
        # Fallback: treat as free-text search with recent time window
        words = re.sub(r"[^\w\s]", " ", lower).split()
        keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 2][:3]
        if keywords:
            parts.append(" ".join(keywords))
            parts.append("date:24h")
            explanations.append("Keyword search over last 24 hours")
        else:
            parts.append("severity:critical date:24h")
            explanations.append("Default: critical activity in last 24 hours")

    siem_query = " ".join(parts)
    explanation = "; ".join(explanations) if explanations else "Converted from natural language"
    confidence = "high" if len(explanations) >= 2 else "medium" if explanations else "low"
    return siem_query, explanation, confidence


_STOP_WORDS = {
    "show", "me", "find", "get", "list", "all", "the", "a", "an", "from", "with",
    "that", "have", "has", "been", "any", "are", "were", "what", "where", "when",
    "please", "search", "for", "events", "event", "alerts", "alert", "logs", "log",
}


def _explain_part(siem_part: str) -> str:
    mapping = {
        "event_type:ssh_login_failure": "Matched failed login / brute-force intent",
        "event_type:sudo_usage": "Matched privilege escalation intent",
        "event_type:port_scan": "Matched port scan intent",
        "severity:critical status:open": "Matched open critical alerts",
        "severity:high status:open": "Matched open high-severity alerts",
        "status:open": "Matched open alert status",
        "status:resolved": "Matched resolved alerts",
        "severity:critical": "Matched critical severity",
        "severity:high": "Matched high severity",
        "event_type:network_flow": "Matched network traffic intent",
        "event_type:malware_detected": "Matched malware intent",
        "event_type:file_integrity": "Matched file integrity intent",
    }
    return mapping.get(siem_part, f"Applied filter {siem_part}")


async def nl_to_siem_query(text: str) -> dict:
    siem_query, explanation, confidence = nl_to_siem_query_local(text)
    provider = resolve_provider()

    if provider != "local":
        llm_result = await call_llm(
            f"You convert natural language SOC search requests into {PRODUCT_NAME} SIEM query syntax. "
            "Use field:value tokens: host, severity, event_type, username, source_ip, status, date. "
            "Date presets: 15m, 30m, 1h, 6h, 12h, 24h, 7d, 30d. "
            "Reply with ONLY the SIEM query string, no explanation.",
            text,
        )
        if llm_result:
            cleaned = llm_result.strip().strip('"').strip("'")
            if cleaned and len(cleaned) < 300:
                return {
                    "siem_query": cleaned,
                    "explanation": f"LLM-refined query ({provider})",
                    "provider": provider,
                    "confidence": "high",
                }

    return {
        "siem_query": siem_query,
        "explanation": explanation,
        "provider": "local",
        "confidence": confidence,
    }
