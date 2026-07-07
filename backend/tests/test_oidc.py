"""Unit tests for OIDC SSO helpers."""

import pytest
from datetime import datetime, timedelta, timezone

from app.security import create_oidc_state_token, decode_oidc_state_token, _encode
from app.services.oidc import build_authorization_url, oidc_configured, oidc_redirect_uri, safe_next_path


def test_oidc_configured_false_by_default():
    assert oidc_configured() is False


def test_safe_next_path_rejects_external():
    assert safe_next_path("https://evil.com") == "/"
    assert safe_next_path("/alerts") == "/alerts"


def test_oidc_state_roundtrip():
    state = create_oidc_state_token(next_path="/offenses", nonce="abc123")
    payload = decode_oidc_state_token(state)
    assert payload["type"] == "oidc_state"
    assert payload["next"] == "/offenses"
    assert payload["nonce"] == "abc123"


def test_build_authorization_url_includes_params():
    discovery = {"authorization_endpoint": "https://idp.example.com/authorize"}
    url = build_authorization_url(discovery, "state-token", "nonce-value")
    assert url.startswith("https://idp.example.com/authorize?")
    assert "state=state-token" in url
    assert "nonce=nonce-value" in url
    assert "redirect_uri=" in url


def test_decode_oidc_state_rejects_wrong_type():
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    token = _encode({"type": "access", "sub": "x", "exp": expire})
    with pytest.raises(Exception):
        decode_oidc_state_token(token)
