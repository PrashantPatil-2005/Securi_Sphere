"""Unit tests for SIEM OpenSearch query builder."""

from datetime import datetime, timezone

from app.search.siem_opensearch import build_siem_index_query
from app.services.siem_search import parse_siem_query
from app.utils.query import TimeRange


def _tr() -> TimeRange:
    return TimeRange(
        from_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        to_time=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )


def test_build_events_query_with_field_filters():
    parsed = parse_siem_query('host:web01 severity:critical event_type:failed_login username:root')
    body = build_siem_index_query(parsed, _tr(), index_kind="events", limit=25)

    assert body["size"] == 25
    must = body["query"]["bool"]["must"]
    assert {"range": {"timestamp": {"gte": "2026-01-01T00:00:00+00:00"}}} in must
    assert {"term": {"severity": "critical"}} in must
    assert {"term": {"event_type": "ssh_login_failure"}} in must
    assert any("host_name" in clause.get("wildcard", {}) for clause in must)
    assert any("username" in clause.get("wildcard", {}) for clause in must)


def test_build_alerts_query_with_status_filter():
    parsed = parse_siem_query("severity:high status:open host:db01")
    body = build_siem_index_query(parsed, _tr(), index_kind="alerts", limit=10)

    must = body["query"]["bool"]["must"]
    assert {"term": {"status": "open"}} in must
    assert {"term": {"severity": "high"}} in must
    assert body["sort"] == [{"created_at": "desc"}]


def test_build_events_query_with_free_text():
    parsed = parse_siem_query("severity:medium suspicious activity")
    body = build_siem_index_query(parsed, _tr(), index_kind="events", limit=50)

    must = body["query"]["bool"]["must"]
    assert any("multi_match" in clause for clause in must)
    mm = next(c["multi_match"] for c in must if "multi_match" in c)
    assert mm["query"] == "suspicious activity"


def test_parse_siem_query_date_preset():
    parsed = parse_siem_query("date:last_7_days severity:low")
    assert parsed["preset"] == "7d"
    assert parsed["filters"]["severity"] == "low"
