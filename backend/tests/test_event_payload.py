from app.pipeline.event_payload import (
    coerce_event_ingests,
    flatten_event_items,
    parse_events_body,
    safe_inet,
)


def test_safe_inet_accepts_ipv4():
    assert safe_inet("10.0.0.8") == "10.0.0.8"


def test_safe_inet_rejects_garbage():
    assert safe_inet("not-an-ip") is None
    assert safe_inet("") is None
    assert safe_inet(None) is None


def test_flatten_nested_wrapper():
    inner = {"event_type": "ssh_login_failure", "severity": "medium", "timestamp": "2026-09-06T00:00:00Z"}
    flat = flatten_event_items([{"events": [inner]}])
    assert flat == [inner]


def test_coerce_skips_metrics_and_keeps_events():
    events, errors = coerce_event_ingests(
        [
            {
                "event_type": "ssh_login_failure",
                "severity": "medium",
                "timestamp": "2026-09-06T00:00:00Z",
                "source": "auth.log",
            },
            {"cpu_percent": 1.0, "recorded_at": "2026-09-06T00:00:00Z"},
        ]
    )
    assert len(events) == 1
    assert events[0].event_type == "ssh_login_failure"
    assert any("metric payload" in e for e in errors)


def test_coerce_truncates_source():
    events, errors = coerce_event_ingests(
        [
            {
                "event_type": "ssh_login_failure",
                "severity": "medium",
                "timestamp": "2026-09-06T00:00:00Z",
                "source": "x" * 80,
            }
        ]
    )
    assert errors == []
    assert len(events[0].source) == 50


def test_parse_events_body_rejects_bad_json():
    items, err = parse_events_body(b"{not json")
    assert items is None
    assert err == "Invalid JSON"


def test_parse_events_body_accepts_v3_batch():
    items, err = parse_events_body(b'{"events":[]}')
    assert err is None
    assert items == []
