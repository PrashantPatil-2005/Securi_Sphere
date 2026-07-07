"""Compliance framework control definitions — SOC 2 and ISO 27001 subsets."""

from __future__ import annotations

from typing import Any, Callable

from app.brand import PRODUCT_NAME

ControlEvaluator = Callable[[dict[str, Any]], dict[str, Any]]


def _status(pass_cond: bool, partial_cond: bool = False) -> str:
    if pass_cond:
        return "pass"
    if partial_cond:
        return "partial"
    return "fail"


def _result(status: str, findings: list[str], recommendation: str | None = None) -> dict[str, Any]:
    return {"status": status, "findings": findings, "recommendation": recommendation}


def _eval_soc2_cc61(ev: dict) -> dict:
    findings = [
        f"RBAC roles defined: {ev['role_count']}",
        f"Active users: {ev['active_users']}",
        f"OIDC/SSO enabled: {ev['oidc_enabled']}",
    ]
    status = _status(ev["role_count"] >= 3 and ev["active_users"] >= 1, ev["active_users"] >= 1)
    return _result(status, findings, None if status == "pass" else "Enable SSO and enforce role-based provisioning.")


def _eval_soc2_cc62(ev: dict) -> dict:
    findings = [
        f"Login audit events (period): {ev['login_audit_events']}",
        f"Account lockout configured: {ev['lockout_enabled']}",
        f"Failed auth events detected: {ev['failed_login_events']}",
    ]
    status = _status(ev["login_audit_events"] > 0 and ev["lockout_enabled"], ev["login_audit_events"] > 0)
    return _result(status, findings, "Ensure all authentication attempts are logged and lockout is enabled.")


def _eval_soc2_cc63(ev: dict) -> dict:
    findings = [
        f"Admin users: {ev['admin_users']}",
        f"Analyst users: {ev['analyst_users']}",
        f"Role change audit events: {ev['role_change_events']}",
    ]
    status = _status(ev["admin_users"] >= 1 and ev["role_count"] >= 3, ev["role_count"] >= 2)
    return _result(status, findings, "Maintain least-privilege roles and audit role changes.")


def _eval_soc2_cc71(ev: dict) -> dict:
    findings = [
        f"Detection rules enabled: {ev['detection_rules_enabled']}",
        f"Alerts created (period): {ev['alerts_created_period']}",
        f"Security events ingested (period): {ev['events_period']}",
    ]
    status = _status(ev["detection_rules_enabled"] >= 1 and ev["events_period"] > 0, ev["events_period"] > 0)
    return _result(status, findings, "Enable detection rules and ensure agents are ingesting events.")


def _eval_soc2_cc72(ev: dict) -> dict:
    findings = [
        f"Hosts monitored: {ev['hosts_monitored']}/{ev['hosts_total']} ({ev['agent_coverage_pct']}%)",
        f"UEBA enabled: {ev['ueba_enabled']}",
        f"Open UEBA anomalies: {ev['ueba_open']}",
    ]
    status = _status(ev["agent_coverage_pct"] >= 80 and ev["events_period"] > 0, ev["hosts_monitored"] > 0)
    return _result(status, findings, "Increase agent coverage above 80% and enable UEBA baselines.")


def _eval_soc2_cc73(ev: dict) -> dict:
    findings = [
        f"Open incidents: {ev['incidents_open']}",
        f"Open offenses: {ev['offenses_open']}",
        f"Incidents created (period): {ev['incidents_created_period']}",
    ]
    status = _status(ev["incidents_created_period"] > 0 or ev["offenses_open"] == 0, True)
    return _result(status, findings, "Document incident procedures and promote offenses to incidents.")


def _eval_soc2_cc74(ev: dict) -> dict:
    findings = [
        f"Alert resolution rate (period): {ev['resolution_rate']}%",
        f"Alerts resolved (period): {ev['alerts_resolved_period']}",
        f"Playbooks configured: {ev['playbooks_count']}",
    ]
    status = _status(ev["resolution_rate"] >= 50 or ev["alerts_created_period"] == 0, ev["resolution_rate"] >= 25)
    return _result(status, findings, "Target ≥50% alert resolution within SLA; configure SOAR playbooks.")


def _eval_soc2_cc81(ev: dict) -> dict:
    findings = [
        f"Audit log events (period): {ev['audit_events_period']}",
        f"Config change events: {ev['config_change_events']}",
    ]
    status = _status(ev["audit_events_period"] >= 10, ev["audit_events_period"] > 0)
    return _result(status, findings, "Ensure administrative actions generate audit trail entries.")


def _eval_iso_a515(ev: dict) -> dict:
    return _eval_soc2_cc61(ev)


def _eval_iso_a516(ev: dict) -> dict:
    findings = [
        f"Active users: {ev['active_users']}",
        f"User provisioning audit events: {ev['user_provision_events']}",
        f"OIDC auto-provision: {ev['oidc_auto_provision']}",
    ]
    status = _status(ev["active_users"] >= 1, ev["active_users"] >= 1)
    return _result(status, findings, "Use admin provisioning or SSO with controlled auto-provision.")


def _eval_iso_a517(ev: dict) -> dict:
    return _eval_soc2_cc62(ev)


def _eval_iso_a524(ev: dict) -> dict:
    return _eval_soc2_cc73(ev)


def _eval_iso_a815(ev: dict) -> dict:
    findings = [
        f"Audit events (period): {ev['audit_events_period']}",
        f"Security events retained: {ev['events_period']}",
        f"Retention policy: {ev['retention_days']} days",
    ]
    status = _status(ev["audit_events_period"] > 0 and ev["retention_days"] >= 30, ev["events_period"] > 0)
    return _result(status, findings, "Maintain ≥30 day retention and continuous event logging.")


def _eval_iso_a816(ev: dict) -> dict:
    return _eval_soc2_cc72(ev)


def _eval_iso_a88(ev: dict) -> dict:
    findings = [
        f"Critical/high open alerts: {ev['critical_high_open']}",
        f"Threat scores computed: {ev['hosts_scored']}",
        f"Detection rules enabled: {ev['detection_rules_enabled']}",
    ]
    status = _status(ev["detection_rules_enabled"] >= 1 and ev["critical_high_open"] == 0, ev["detection_rules_enabled"] >= 1)
    return _result(status, findings, "Resolve critical/high alerts and maintain detection coverage.")


COMPLIANCE_FRAMEWORKS: dict[str, dict[str, Any]] = {
    "soc2": {
        "id": "soc2",
        "name": "SOC 2 Type II",
        "description": f"Trust Services Criteria subset mapped to {PRODUCT_NAME} evidence",
        "controls": [
            {"id": "CC6.1", "title": "Logical access security", "category": "Common Criteria — Logical Access",
             "requirement": "The entity implements logical access security software and rules.", "evaluate": _eval_soc2_cc61},
            {"id": "CC6.2", "title": "User authentication", "category": "Common Criteria — Logical Access",
             "requirement": "Prior to issuing credentials, user identity is verified and credentials are protected.", "evaluate": _eval_soc2_cc62},
            {"id": "CC6.3", "title": "Role-based authorization", "category": "Common Criteria — Logical Access",
             "requirement": "Access is authorized and modified based on roles and least privilege.", "evaluate": _eval_soc2_cc63},
            {"id": "CC7.1", "title": "Detection of security events", "category": "Common Criteria — System Operations",
             "requirement": "Procedures detect and report security events and configuration changes.", "evaluate": _eval_soc2_cc71},
            {"id": "CC7.2", "title": "Security monitoring", "category": "Common Criteria — System Operations",
             "requirement": "Security events are monitored and anomalies are identified.", "evaluate": _eval_soc2_cc72},
            {"id": "CC7.3", "title": "Incident response", "category": "Common Criteria — System Operations",
             "requirement": "Security incidents are identified, reported, and acted upon.", "evaluate": _eval_soc2_cc73},
            {"id": "CC7.4", "title": "Response to identified security events", "category": "Common Criteria — System Operations",
             "requirement": "Identified security events are evaluated and responded to timely.", "evaluate": _eval_soc2_cc74},
            {"id": "CC8.1", "title": "Change management audit trail", "category": "Common Criteria — Change Management",
             "requirement": "Changes are authorized, tested, and logged.", "evaluate": _eval_soc2_cc81},
        ],
    },
    "iso27001": {
        "id": "iso27001",
        "name": "ISO/IEC 27001:2022",
        "description": "Annex A control subset with platform evidence",
        "controls": [
            {"id": "A.5.15", "title": "Access control", "category": "Organizational controls",
             "requirement": "Rules to control physical and logical access to information are established.", "evaluate": _eval_iso_a515},
            {"id": "A.5.16", "title": "Identity management", "category": "Organizational controls",
             "requirement": "The full life cycle of identities is managed.", "evaluate": _eval_iso_a516},
            {"id": "A.5.17", "title": "Authentication information", "category": "Organizational controls",
             "requirement": "Allocation and management of authentication information is controlled.", "evaluate": _eval_iso_a517},
            {"id": "A.5.24", "title": "Information security incident management", "category": "Organizational controls",
             "requirement": "Incidents are managed according to documented procedures.", "evaluate": _eval_iso_a524},
            {"id": "A.8.15", "title": "Logging", "category": "Technological controls",
             "requirement": "Logs recording activities, exceptions, and security events are produced and kept.", "evaluate": _eval_iso_a815},
            {"id": "A.8.16", "title": "Monitoring activities", "category": "Technological controls",
             "requirement": "Networks, systems, and applications are monitored for anomalous behaviour.", "evaluate": _eval_iso_a816},
            {"id": "A.8.8", "title": "Management of technical vulnerabilities", "category": "Technological controls",
             "requirement": "Information about technical vulnerabilities is obtained and addressed.", "evaluate": _eval_iso_a88},
        ],
    },
}


def list_frameworks() -> list[dict[str, Any]]:
    return [
        {"id": fw["id"], "name": fw["name"], "description": fw["description"], "control_count": len(fw["controls"])}
        for fw in COMPLIANCE_FRAMEWORKS.values()
    ]


def evaluate_framework(framework_id: str, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    fw = COMPLIANCE_FRAMEWORKS.get(framework_id)
    if not fw:
        raise ValueError(f"Unknown framework: {framework_id}")
    results = []
    for ctrl in fw["controls"]:
        evaluated = ctrl["evaluate"](evidence)
        results.append({
            "id": ctrl["id"],
            "title": ctrl["title"],
            "category": ctrl["category"],
            "requirement": ctrl["requirement"],
            **evaluated,
        })
    return results
