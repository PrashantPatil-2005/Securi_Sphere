"""Unit tests for compliance control evaluation."""

from app.services.compliance_templates import evaluate_framework


def _base_evidence() -> dict:
    return {
        "audit_events_period": 50,
        "login_audit_events": 10,
        "role_change_events": 2,
        "config_change_events": 5,
        "user_provision_events": 1,
        "role_count": 3,
        "active_users": 5,
        "admin_users": 1,
        "analyst_users": 2,
        "oidc_enabled": True,
        "oidc_auto_provision": False,
        "lockout_enabled": True,
        "hosts_total": 10,
        "hosts_monitored": 9,
        "agent_coverage_pct": 90.0,
        "events_period": 1000,
        "failed_login_events": 5,
        "alerts_created_period": 10,
        "alerts_resolved_period": 8,
        "resolution_rate": 80.0,
        "critical_high_open": 0,
        "detection_rules_enabled": 5,
        "incidents_open": 1,
        "incidents_created_period": 2,
        "offenses_open": 0,
        "ueba_enabled": True,
        "ueba_open": 0,
        "playbooks_count": 2,
        "hosts_scored": 10,
        "retention_days": 90,
    }


def test_soc2_evaluation_pass_majority():
    results = evaluate_framework("soc2", _base_evidence())
    assert len(results) == 8
    assert sum(1 for r in results if r["status"] == "pass") >= 5


def test_iso27001_evaluation():
    results = evaluate_framework("iso27001", _base_evidence())
    assert len(results) == 7
    assert all("findings" in r for r in results)
