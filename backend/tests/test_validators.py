"""Unit tests for shared Pydantic validators."""

from ipaddress import IPv4Address

from app.schemas.validators import coerce_inet_to_str


def test_coerce_inet_to_str_from_ipv4():
    assert coerce_inet_to_str(IPv4Address("192.168.1.10")) == "192.168.1.10"


def test_coerce_inet_to_str_from_string():
    assert coerce_inet_to_str("10.0.0.1") == "10.0.0.1"


def test_coerce_inet_to_str_none():
    assert coerce_inet_to_str(None) is None
