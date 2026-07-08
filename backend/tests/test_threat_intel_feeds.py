"""Unit tests for threat intel feed parsing."""

from app.services.threat_intel_feeds import parse_feed_values


def test_parse_txt_feed_values():
    payload = "1.1.1.1\n#comment\n 2.2.2.2 \n1.1.1.1\n"
    assert parse_feed_values(payload, "txt") == ["1.1.1.1", "2.2.2.2"]


def test_parse_csv_feed_values():
    payload = "value,note\nbad.com,test\nevil.com,foo\nbad.com,dup\n"
    assert parse_feed_values(payload, "csv") == ["bad.com", "evil.com"]


def test_parse_json_feed_values():
    payload = '[{"value":"198.51.100.1"},{"indicator":"bad.example"}, "1.1.1.1"]'
    assert parse_feed_values(payload, "json") == ["198.51.100.1", "bad.example", "1.1.1.1"]
