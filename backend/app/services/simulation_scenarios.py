"""Attack simulation scenario definitions."""

from dataclasses import dataclass, field

from app.services.mitre import EVENT_MITRE_MAP


@dataclass
class ScenarioStep:
    event_type: str
    offset_seconds: int
    description: str | None = None


@dataclass
class ScenarioDef:
    id: str
    name: str
    summary: str
    difficulty: str
    expected_alerts: list[str]
    expected_outcomes: list[str]
    steps: list[ScenarioStep] = field(default_factory=list)


SCENARIO_DEFS: dict[str, ScenarioDef] = {
    "multi_stage_attack": ScenarioDef(
        id="multi_stage_attack",
        name="Multi-Stage Attack",
        summary="Brute force → access → sudo → C2 flow → service impact",
        difficulty="advanced",
        expected_alerts=["brute_force", "failed_logins"],
        expected_outcomes=["offense", "attack_timeline"],
        steps=[
            ScenarioStep("ssh_login_failure", 0),
            ScenarioStep("ssh_login_failure", 25),
            ScenarioStep("ssh_login_failure", 50),
            ScenarioStep("ssh_login_failure", 75),
            ScenarioStep("ssh_login_failure", 100),
            ScenarioStep("ssh_login_success", 120),
            ScenarioStep("sudo_usage", 180),
            ScenarioStep("network_flow", 240),
            ScenarioStep("service_failure", 300),
        ],
    ),
    "brute_force": ScenarioDef(
        id="brute_force",
        name="Brute Force",
        summary="Repeated SSH failures followed by successful login and sudo",
        difficulty="intermediate",
        expected_alerts=["brute_force", "failed_logins"],
        expected_outcomes=["offense", "attack_timeline"],
        steps=[
            ScenarioStep("ssh_login_failure", 0),
            ScenarioStep("ssh_login_failure", 30),
            ScenarioStep("ssh_login_failure", 60),
            ScenarioStep("ssh_login_failure", 90),
            ScenarioStep("ssh_login_failure", 120),
            ScenarioStep("ssh_login_success", 150),
            ScenarioStep("sudo_usage", 180),
        ],
    ),
    "brute_force_only": ScenarioDef(
        id="brute_force_only",
        name="Brute Force Only",
        summary="Six consecutive SSH login failures with no successful access",
        difficulty="beginner",
        expected_alerts=["brute_force", "failed_logins"],
        expected_outcomes=["offense"],
        steps=[ScenarioStep("ssh_login_failure", i * 20) for i in range(6)],
    ),
    "service_crash": ScenarioDef(
        id="service_crash",
        name="Service Crash",
        summary="Single critical service failure event",
        difficulty="beginner",
        expected_alerts=["service_failure"],
        expected_outcomes=[],
        steps=[ScenarioStep("service_failure", 0)],
    ),
}


def get_scenario(scenario_id: str) -> ScenarioDef | None:
    return SCENARIO_DEFS.get(scenario_id)


def mitre_for_event_type(event_type: str) -> dict | None:
    mapping = EVENT_MITRE_MAP.get(event_type)
    if not mapping:
        return None
    return {
        "technique_id": mapping["technique_id"],
        "tactic": mapping["tactic"],
        "name": mapping["name"],
    }


def scenario_to_api(scenario: ScenarioDef) -> dict:
    steps = []
    max_offset = 0
    for i, step in enumerate(scenario.steps, start=1):
        max_offset = max(max_offset, step.offset_seconds)
        steps.append({
            "order": i,
            "event_type": step.event_type,
            "offset_seconds": step.offset_seconds,
            "description": step.description,
            "mitre": mitre_for_event_type(step.event_type),
        })
    return {
        "id": scenario.id,
        "name": scenario.name,
        "summary": scenario.summary,
        "difficulty": scenario.difficulty,
        "event_count": len(scenario.steps),
        "duration_seconds": max_offset,
        "steps": steps,
        "expected_alerts": scenario.expected_alerts,
        "expected_outcomes": scenario.expected_outcomes,
    }


def list_scenarios_api() -> list[dict]:
    return [scenario_to_api(s) for s in SCENARIO_DEFS.values()]
