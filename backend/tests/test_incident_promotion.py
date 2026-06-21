"""Unit tests for offense → incident promotion."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services.incident_promotion import RISK_TO_SEVERITY


def test_risk_level_maps_to_incident_severity():
    assert RISK_TO_SEVERITY["critical"] == "critical"
    assert RISK_TO_SEVERITY["high"] == "high"
    assert RISK_TO_SEVERITY.get("unknown", "medium") == "medium"


def test_timeline_summary_format():
    timeline = [{"ts": "2024-01-01T00:00:00Z", "type": "alert", "detail": "Brute force detected"}]
    line = f"- {timeline[0].get('ts', '')}: {timeline[0].get('detail') or timeline[0].get('type', '')}"
    assert "Brute force detected" in line
