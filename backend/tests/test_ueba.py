"""Unit tests for UEBA z-score logic."""

from app.services.ueba import compute_z_score, severity_from_z


def test_compute_z_score():
    assert compute_z_score(20, 5, 2) == 7.5
    assert compute_z_score(5, 5, 0) == 0.0


def test_severity_from_z():
    assert severity_from_z(5.1) == "critical"
    assert severity_from_z(4) == "high"
    assert severity_from_z(3) == "medium"
    assert severity_from_z(2.5) == "low"
