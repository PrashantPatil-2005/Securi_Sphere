"""Tests for the 3 new demo scenarios."""

import pytest
from app.services.simulation_scenarios import (
    SCENARIO_DEFS,
    get_scenario,
    list_scenarios_api,
    scenario_to_api,
)


# ── Scenario definition tests ──


def test_all_three_scenarios_exist():
    """The 3 primary demo scenarios must be defined."""
    for scenario_id in ("brute_force_attack", "host_health_crisis", "soc_resilience"):
        scenario = get_scenario(scenario_id)
        assert scenario is not None, f"Missing scenario: {scenario_id}"


def test_legacy_scenarios_still_exist():
    """Legacy scenarios must not be removed."""
    for scenario_id in ("multi_stage_attack", "brute_force", "brute_force_only", "service_crash"):
        scenario = get_scenario(scenario_id)
        assert scenario is not None, f"Missing legacy scenario: {scenario_id}"


def test_brute_force_attack_scenario():
    """Scenario 1: Brute Force Attack should have auth events + escalation."""
    s = get_scenario("brute_force_attack")
    assert s.name == "Brute Force Attack"
    assert s.difficulty == "intermediate"
    assert len(s.steps) >= 8

    event_types = [step.event_type for step in s.steps]
    # Must have multiple SSH failures
    assert event_types.count("ssh_login_failure") >= 5
    # Must have successful login after failures
    assert "ssh_login_success" in event_types
    # Must have privilege escalation
    assert "sudo_usage" in event_types
    # Must have service impact
    assert "service_failure" in event_types

    # Steps should have descriptions
    assert all(step.description for step in s.steps)

    # Expected outcomes
    assert "offense" in s.expected_outcomes
    assert "attack_timeline" in s.expected_outcomes
    assert "mitre_mapping" in s.expected_outcomes


def test_host_health_crisis_scenario():
    """Scenario 2: Host Health Incident should have resource pressure events."""
    s = get_scenario("host_health_crisis")
    assert s.name == "Host Health Incident"
    assert s.difficulty == "beginner"
    assert len(s.steps) >= 6

    event_types = [step.event_type for step in s.steps]
    # Must have CPU events
    assert "high_cpu" in event_types
    # Must have memory events
    assert "high_memory" in event_types
    # Must have disk events
    assert "high_disk" in event_types
    # Must have service failure
    assert "service_failure" in event_types
    # Must have agent disconnect
    assert "agent_disconnect" in event_types

    # Steps should have severity values
    severity_steps = [step for step in s.steps if step.severity]
    assert len(severity_steps) >= 4

    # Expected outcomes
    assert "host_risk_change" in s.expected_outcomes
    assert "status_change" in s.expected_outcomes


def test_soc_resilience_scenario():
    """Scenario 3: SOC Resilience should demonstrate buffering concept."""
    s = get_scenario("soc_resilience")
    assert s.name == "SOC Resilience"
    assert s.difficulty == "advanced"
    assert len(s.steps) >= 8

    event_types = [step.event_type for step in s.steps]
    # Must have SSH failures
    assert "ssh_login_failure" in event_types
    # Must have metric events
    assert "high_cpu" in event_types
    assert "high_memory" in event_types
    # Must have successful login after recovery
    assert "ssh_login_success" in event_types

    # Descriptions should indicate buffering phases
    descriptions = [step.description or "" for step in s.steps]
    buffered_steps = [d for d in descriptions if "BUFFERED" in d]
    replay_steps = [d for d in descriptions if "REPLAY" in d]
    assert len(buffered_steps) >= 3, "Should have buffered event phases"
    assert len(replay_steps) >= 2, "Should have replay event phases"

    # Expected outcomes
    assert "buffered_replay" in s.expected_outcomes
    assert "deduplication" in s.expected_outcomes


# ── API serialization tests ──


def test_scenario_to_api_includes_severity():
    """API serialization should include severity when present."""
    s = get_scenario("host_health_crisis")
    api_data = scenario_to_api(s)
    assert api_data["id"] == "host_health_crisis"
    assert api_data["name"] == "Host Health Incident"

    # Check that severity is included in steps
    severity_steps = [step for step in api_data["steps"] if step.get("severity")]
    assert len(severity_steps) >= 4


def test_list_scenarios_api_includes_new_scenarios():
    """The API list should include all 3 new scenarios."""
    scenarios = list_scenarios_api()
    ids = [s["id"] for s in scenarios]
    assert "brute_force_attack" in ids
    assert "host_health_crisis" in ids
    assert "soc_resilience" in ids
    # Legacy should also be present
    assert "multi_stage_attack" in ids
    assert "brute_force" in ids


def test_scenario_api_has_mitre_mapping():
    """Scenarios with auth events should have MITRE mappings in steps."""
    s = get_scenario("brute_force_attack")
    api_data = scenario_to_api(s)

    # SSH failure steps should have MITRE technique
    auth_steps = [
        step for step in api_data["steps"]
        if step["event_type"] in ("ssh_login_failure", "ssh_login_success", "sudo_usage")
    ]
    assert len(auth_steps) >= 3
    for step in auth_steps:
        assert step["mitre"] is not None
        assert "technique_id" in step["mitre"]


# ── Pipeline path verification ──


def test_scenario_event_types_are_in_allowed_list():
    """All event types in scenarios must be in the allowed event types list."""
    from app.services.simulation_runner import ALLOWED_EVENT_TYPES

    for scenario_id, scenario in SCENARIO_DEFS.items():
        for step in scenario.steps:
            assert step.event_type in ALLOWED_EVENT_TYPES, (
                f"Scenario '{scenario_id}' uses unsupported event type '{step.event_type}'"
            )
