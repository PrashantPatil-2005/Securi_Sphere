"""Unit tests for natural language SIEM search."""

from app.services.ai.nl_search import nl_to_siem_query_local


def test_nl_sudo_events():
    query, explanation, _ = nl_to_siem_query_local("privilege escalation via sudo last 7 days")
    assert "event_type:sudo_usage" in query
    assert "date:7d" in query
    assert "privilege" in explanation.lower() or "Matched" in explanation


def test_nl_username_filter():
    query, _, _ = nl_to_siem_query_local("failed login for user root")
    assert "username:root" in query
    assert "event_type:ssh_login_failure" in query


def test_nl_source_ip():
    query, _, _ = nl_to_siem_query_local("events from 192.168.1.50")
    assert "source_ip:192.168.1.50" in query


def test_nl_open_alerts():
    query, _, confidence = nl_to_siem_query_local("list open alerts")
    assert "status:open" in query
    assert confidence in ("high", "medium", "low")


def test_nl_fallback_keywords():
    query, _, _ = nl_to_siem_query_local("suspicious activity")
    assert "date:24h" in query
