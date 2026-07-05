"""Unit tests for local AI assistant (no external API)."""

import pytest

from app.services.ai.assistant import _local_chat_reply
from app.services.ai.nl_search import nl_to_siem_query_local


def test_nl_failed_logins_last_hour():
    query, explanation, confidence = nl_to_siem_query_local("Show failed logins from last hour")
    assert "event_type:ssh_login_failure" in query
    assert "date:1h" in query
    assert confidence in ("high", "medium", "low")
    assert explanation


def test_nl_critical_alerts():
    query, _, _ = nl_to_siem_query_local("Find all critical alerts")
    assert "severity:critical" in query
    assert "status:open" in query


def test_nl_host_filter():
    query, _, _ = nl_to_siem_query_local("Show events from host web01")
    assert "host:web01" in query


def test_nl_brute_force():
    query, _, _ = nl_to_siem_query_local("brute force attempts in the last 24 hours")
    assert "event_type:ssh_login_failure" in query
    assert "date:24h" in query


def test_assistant_explain_alert_context():
    ctx = {
        "type": "alert",
        "alert": {
            "title": "SSH brute force detected",
            "severity": "high",
            "status": "open",
            "description": "Multiple failed SSH logins",
            "mitre_technique_id": "T1110",
            "confidence": 85,
        },
        "host": {"name": "lab-vm", "status": "warning", "risk_score": 62},
        "recent_events": [],
    }
    reply, suggestions = _local_chat_reply("Explain this alert", ctx, None)
    assert "SSH brute force" in reply
    assert "lab-vm" in reply
    assert len(suggestions) >= 1


def test_assistant_investigation_steps():
    ctx = {
        "type": "alert",
        "alert": {"title": "Test", "severity": "critical", "status": "open"},
        "host": {"name": "srv1", "status": "online"},
        "recent_events": [],
    }
    reply, _ = _local_chat_reply("What investigation steps should I take?", ctx, None)
    assert "Investigation playbook" in reply or "investigating" in reply.lower()


def test_assistant_siem_syntax_help():
    reply, _ = _local_chat_reply("How does SIEM query syntax work?", None, None)
    assert "field:value" in reply or "host:" in reply


@pytest.mark.asyncio
async def test_assistant_chat_endpoint(analyst_client):
    res = await analyst_client.post(
        "/api/v1/assistant/chat",
        json={"message": "Hello, what can you help with?"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["provider"] == "local"
    assert len(body["reply"]) > 10
    assert isinstance(body["suggestions"], list)


@pytest.mark.asyncio
async def test_nl_search_endpoint(analyst_client):
    res = await analyst_client.post(
        "/api/v1/search/nl",
        json={"query": "Show failed logins from last hour"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "event_type:ssh_login_failure" in body["siem_query"]
    assert body["provider"] == "local"


@pytest.mark.asyncio
async def test_assistant_requires_auth(client):
    res = await client.post(
        "/api/v1/assistant/chat",
        json={"message": "test"},
    )
    assert res.status_code == 401
