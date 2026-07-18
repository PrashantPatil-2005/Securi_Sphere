"""Tests for agent authentication — HMAC signing, verification, validation."""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.agent_auth import (
    MAX_CLOCK_SKEW_SECONDS,
    NONCE_RETENTION_HOURS,
    sign_payload,
    verify_agent_signature,
)


# ---------------------------------------------------------------------------
# sign_payload
# ---------------------------------------------------------------------------

def test_sign_payload_deterministic():
    body = b'{"events":[]}'
    sig1 = sign_payload("key123", "2026-01-01T00:00:00Z", "abc", body)
    sig2 = sign_payload("key123", "2026-01-01T00:00:00Z", "abc", body)
    assert sig1 == sig2


def test_sign_payload_differs_with_different_key():
    body = b'{"events":[]}'
    sig1 = sign_payload("key1", "2026-01-01T00:00:00Z", "abc", body)
    sig2 = sign_payload("key2", "2026-01-01T00:00:00Z", "abc", body)
    assert sig1 != sig2


def test_sign_payload_differs_with_different_nonce():
    body = b'{"events":[]}'
    sig1 = sign_payload("key123", "2026-01-01T00:00:00Z", "nonce1", body)
    sig2 = sign_payload("key123", "2026-01-01T00:00:00Z", "nonce2", body)
    assert sig1 != sig2


def test_sign_payload_differs_with_different_body():
    body1 = b'{"events":[]}'
    body2 = b'{"events":[{"type":"test"}]}'
    sig1 = sign_payload("key123", "2026-01-01T00:00:00Z", "abc", body1)
    sig2 = sign_payload("key123", "2026-01-01T00:00:00Z", "abc", body2)
    assert sig1 != sig2


def test_sign_payload_is_hex():
    body = b'test'
    sig = sign_payload("key", "ts", "nonce", body)
    assert len(sig) == 64  # SHA-256 hex
    int(sig, 16)  # Should not raise


# ---------------------------------------------------------------------------
# verify_agent_signature
# ---------------------------------------------------------------------------

def test_verify_agent_signature_valid():
    body = b'{"events":[]}'
    ts = "2026-01-01T00:00:00Z"
    nonce = "abc123"
    api_key = "test-key"
    sig = sign_payload(api_key, ts, nonce, body)
    assert verify_agent_signature(api_key, ts, nonce, sig, body) is True


def test_verify_agent_signature_wrong_key():
    body = b'{"events":[]}'
    ts = "2026-01-01T00:00:00Z"
    nonce = "abc123"
    sig = sign_payload("correct-key", ts, nonce, body)
    assert verify_agent_signature("wrong-key", ts, nonce, sig, body) is False


def test_verify_agent_signature_wrong_body():
    body = b'{"events":[]}'
    ts = "2026-01-01T00:00:00Z"
    nonce = "abc123"
    api_key = "test-key"
    sig = sign_payload(api_key, ts, nonce, body)
    assert verify_agent_signature(api_key, ts, nonce, sig, b'{"events":[{"x":1}]}') is False


def test_verify_agent_signature_wrong_nonce():
    body = b'{"events":[]}'
    ts = "2026-01-01T00:00:00Z"
    api_key = "test-key"
    sig = sign_payload(api_key, ts, "nonce1", body)
    assert verify_agent_signature(api_key, ts, "nonce2", sig, body) is False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_max_clock_skew_is_5_minutes():
    assert MAX_CLOCK_SKEW_SECONDS == 300


def test_nonce_retention_is_24_hours():
    assert NONCE_RETENTION_HOURS == 24


# ---------------------------------------------------------------------------
# sign_payload format verification
# ---------------------------------------------------------------------------

def test_sign_payload_format():
    body = b'{"test": true}'
    ts = "2026-07-18T10:00:00Z"
    nonce = "aabb"
    api_key = "secret"

    message = f"{ts}.{nonce}.".encode() + body
    expected = hmac.new(api_key.encode(), message, hashlib.sha256).hexdigest()
    actual = sign_payload(api_key, ts, nonce, body)
    assert actual == expected
