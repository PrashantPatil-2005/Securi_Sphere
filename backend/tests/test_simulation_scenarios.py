"""Tests for simulation scenarios and pipeline."""
import pytest
from app.services.simulation_scenarios import get_scenario, list_scenarios_api, ScenarioDef, ScenarioStep


def test_scenario_catalog_has_all_six_lab_scenarios():
    """All six Linux activity lab scenarios A-F must be present."""
    scenarios = {s["id"] for s in list_scenarios_api()}
    expected_ids = {
        "brute_force_attack",
        "privilege_escalation",
        "file_integrity",
        "systemd_monitoring",
        "network_reconnaissance",
        "agent_tampering",
    }
    assert expected_ids.issubset(scenarios), f"Missing scenarios: {expected_ids - scenarios}"


def test_scenario_a_brute_force_attack():
    """Scenario A: Brute Force Attack - SSH failures + sudo + service failure."""
    s = get_scenario("brute_force_attack")
    assert s is not None
    assert s.name == "Brute Force Attack"
    assert "brute_force" in s.expected_alerts
    assert "failed_logins" in s.expected_alerts
    # 10 failures (brute force threshold) + success + sudo + service failure
    assert len(s.steps) == 13
    # Verify step event types
    event_types = [step.event_type for step in s.steps]
    assert event_types.count("ssh_login_failure") >= 10
    assert "ssh_login_failure" in event_types
    assert "ssh_login_success" in event_types
    assert "sudo_usage" in event_types
    assert "service_failure" in event_types


def test_scenario_b_privilege_escalation():
    """Scenario B: Privilege Escalation Monitoring - sudo + root login."""
    s = get_scenario("privilege_escalation")
    assert s is not None
    assert s.name == "Privilege Escalation Monitoring"
    assert "privilege_escalation" in s.expected_alerts
    assert "root_login" in s.expected_alerts
    assert len(s.steps) == 5
    event_types = [step.event_type for step in s.steps]
    assert "sudo_usage" in event_types
    assert "root_login" in event_types


def test_scenario_c_file_integrity():
    """Scenario C: File Integrity Monitoring - file change events."""
    s = get_scenario("file_integrity")
    assert s is not None
    assert s.name == "File Integrity Monitoring"
    assert "file_integrity" in s.expected_alerts
    assert len(s.steps) == 4
    event_types = [step.event_type for step in s.steps]
    assert "file_change" in event_types


def test_scenario_d_systemd_monitoring():
    """Scenario D: Systemd Service & Persistence Monitoring."""
    s = get_scenario("systemd_monitoring")
    assert s is not None
    assert s.name == "Systemd Service & Persistence Monitoring"
    assert "service_stop" in s.expected_alerts
    assert "service_failure" in s.expected_alerts
    assert len(s.steps) == 3
    event_types = [step.event_type for step in s.steps]
    assert "service_stop" in event_types
    assert "service_start" in event_types
    assert "service_failure" in event_types


def test_scenario_e_network_reconnaissance():
    """Scenario E: Network Reconnaissance - with explicit limitation note."""
    s = get_scenario("network_reconnaissance")
    assert s is not None
    assert s.name == "Network Reconnaissance"
    # expected_alerts reflects what the synthetic preset raises; live mode
    # additionally raises port_scan when the flow collector is enabled.
    assert "firewall_block" in s.expected_alerts
    # 10 firewall blocks (surge threshold) + 2 flow samples
    assert len(s.steps) == 12
    event_types = [step.event_type for step in s.steps]
    assert "network_flow" in event_types
    assert event_types.count("firewall_block") >= 10
    assert s.live_instructions is not None
    assert "nc" in s.live_instructions
    assert "port_scan" in (s.notes or "")


def test_scenario_f_agent_tampering():
    """Scenario F: Agent Tampering & Heartbeat Loss."""
    s = get_scenario("agent_tampering")
    assert s is not None
    assert s.name == "Agent Tampering & Heartbeat Loss"
    assert "agent_offline" in s.expected_alerts
    assert len(s.steps) == 5
    event_types = [step.event_type for step in s.steps]
    assert "agent_disconnect" in event_types


def test_scenario_catalog_legacy_preserved():
    """Legacy scenarios must still be available for backward compatibility."""
    scenarios = {s["id"] for s in list_scenarios_api()}
    legacy_ids = {"multi_stage_attack", "brute_force", "brute_force_only", "service_crash"}
    assert legacy_ids.issubset(scenarios), f"Missing legacy scenarios: {legacy_ids - scenarios}"


def test_scenario_def_dataclass_fields():
    """ScenarioDef dataclass must have all required fields."""
    s = ScenarioDef(
        id="test",
        name="Test",
        summary="Test summary",
        difficulty="beginner",
        expected_alerts=["alert"],
        expected_outcomes=["outcome"],
        steps=[ScenarioStep(event_type="ssh_login_failure", offset_seconds=0)],
    )
    assert s.id == "test"
    assert s.category == "authentication"  # default
    assert s.live_instructions is None  # default
    assert s.notes is None  # default


# ── Stream pacing ──


def _steps(*offsets: int):
    from app.services.simulation_runner import RunStep

    return [RunStep(event_type="ssh_login_failure", offset_seconds=o) for o in offsets]


def test_instant_pace_never_sleeps():
    from app.services.simulation_runner import _build_delays

    assert _build_delays(_steps(0, 50, 100), "instant") == [0.0, 0.0, 0.0]


def test_stream_pace_spans_the_clamped_window():
    from app.services.simulation_runner import _build_delays

    delays = _build_delays(_steps(0, 50, 100), "stream")
    assert len(delays) == 3
    assert delays[0] == 0.0  # first event lands immediately
    assert sum(delays) == pytest.approx(18.0)  # 100s span clamped to max window
    assert delays[1] > 0 and delays[2] > 0


def test_stream_pace_respects_short_scenarios():
    from app.services.simulation_runner import STREAM_MIN_SECONDS, _build_delays

    assert sum(_build_delays(_steps(0, 1, 2), "stream")) == pytest.approx(
        STREAM_MIN_SECONDS
    )


def test_stream_pace_zero_span_is_instant():
    from app.services.simulation_runner import _build_delays

    assert _build_delays(_steps(0), "stream") == [0.0]
    assert sum(_build_delays(_steps(5, 5), "stream")) == 0.0


def test_stream_pace_honours_explicit_duration():
    from app.services.simulation_runner import _build_delays

    delays = _build_delays(_steps(0, 100, 300), "stream", duration_seconds=4)
    assert sum(delays) == pytest.approx(4.0)
