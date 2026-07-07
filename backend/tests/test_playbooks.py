"""Unit tests for SOAR playbook matching and signing."""

from app.services.playbooks import (
    severity_meets_minimum,
    sign_payload,
    validate_trigger,
)


def test_validate_trigger():
    assert validate_trigger("alert_created") == "alert_created"
    try:
        validate_trigger("invalid")
        assert False
    except ValueError:
        pass


def test_severity_meets_minimum():
    assert severity_meets_minimum("critical", "high")
    assert severity_meets_minimum("high", "high")
    assert not severity_meets_minimum("low", "high")
    assert severity_meets_minimum("medium", None)


def test_sign_payload_deterministic():
    sig = sign_payload("secret", b'{"event":"test"}')
    assert sig == sign_payload("secret", b'{"event":"test"}')
    assert len(sig) == 64
