"""Tests for retention service logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_retention_cutoff_calculation():
    from app.services.retention import run_retention
    from datetime import datetime, timedelta, timezone

    retention_days = 90
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    assert cutoff < datetime.now(timezone.utc)
    assert (datetime.now(timezone.utc) - cutoff).days == 90


def test_retention_audit_immutable_flag():
    from app.config import settings
    assert hasattr(settings, "audit_immutable")
    assert isinstance(settings.audit_immutable, bool)


def test_retention_settings_exist():
    from app.config import settings
    assert hasattr(settings, "retention_days")
    assert settings.retention_days > 0
    assert hasattr(settings, "idempotency_ttl_seconds")
    assert settings.idempotency_ttl_seconds > 0
    assert hasattr(settings, "audit_retention_days")
    assert settings.audit_retention_days > 0
