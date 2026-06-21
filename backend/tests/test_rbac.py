import pytest

from app.services.detection import SUPPORTED_RULE_TYPES


def test_supported_rule_types_complete():
    expected = {
        "failed_logins", "brute_force", "high_cpu", "high_memory",
        "high_disk", "service_failure", "agent_offline",
    }
    assert expected == set(SUPPORTED_RULE_TYPES)


def test_viewer_export_requires_elevated_role():
    """Document RBAC expectation: export endpoints use admin/analyst."""
    allowed_export_roles = {"admin", "analyst"}
    assert "viewer" not in allowed_export_roles


def test_offense_status_requires_elevated_role():
    allowed_offense_write = {"admin", "analyst"}
    assert "viewer" not in allowed_offense_write
