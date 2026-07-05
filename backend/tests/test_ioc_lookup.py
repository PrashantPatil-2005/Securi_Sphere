"""IOC classification tests."""

from app.services.ioc_lookup import classify_ioc


def test_classify_ip():
    assert classify_ioc("203.0.113.10") == "ip"


def test_classify_domain():
    assert classify_ioc("evil.example.com") == "domain"


def test_classify_hash():
    assert classify_ioc("a" * 64) == "file"
