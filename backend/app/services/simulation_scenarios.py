"""Attack simulation scenario definitions."""

from dataclasses import dataclass, field

from app.services.mitre import EVENT_MITRE_MAP


@dataclass
class ScenarioStep:
    event_type: str
    offset_seconds: int
    severity: str | None = None
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
    # ── Scenario 1: Brute Force Attack ──
    "brute_force_attack": ScenarioDef(
        id="brute_force_attack",
        name="Brute Force Attack",
        summary="Repeated SSH authentication failures followed by successful login and privilege escalation",
        difficulty="intermediate",
        expected_alerts=["brute_force", "failed_logins"],
        expected_outcomes=["offense", "attack_timeline", "mitre_mapping"],
        steps=[
            ScenarioStep("ssh_login_failure", 0, description="First failed SSH attempt from attacker"),
            ScenarioStep("ssh_login_failure", 15, description="Second failed attempt — increasing frequency"),
            ScenarioStep("ssh_login_failure", 25, description="Third failed attempt"),
            ScenarioStep("ssh_login_failure", 35, description="Fourth failed attempt"),
            ScenarioStep("ssh_login_failure", 45, description="Fifth failed attempt — brute force threshold approaching"),
            ScenarioStep("ssh_login_failure", 55, description="Sixth failed attempt — triggers failed_logins alert"),
            ScenarioStep("ssh_login_failure", 65, description="Seventh failed attempt"),
            ScenarioStep("ssh_login_failure", 75, description="Eighth failed attempt"),
            ScenarioStep("ssh_login_failure", 85, description="Ninth failed attempt — triggers brute_force alert"),
            ScenarioStep("ssh_login_success", 100, description="Attacker successfully authenticates"),
            ScenarioStep("sudo_usage", 130, description="Attacker escalates to root via sudo"),
            ScenarioStep("service_failure", 160, description="Attacker causes service disruption"),
        ],
    ),
    # ── Scenario 2: Host Health Crisis ──
    "host_health_crisis": ScenarioDef(
        id="host_health_crisis",
        name="Host Health Incident",
        summary="Resource pressure escalation: CPU spike, memory exhaustion, disk full, service failure, and agent offline",
        difficulty="beginner",
        expected_alerts=["high_cpu", "high_memory", "high_disk", "service_failure", "agent_offline"],
        expected_outcomes=["host_risk_change", "status_change"],
        steps=[
            ScenarioStep("high_cpu", 0, severity="medium", description="CPU usage spikes to 95%"),
            ScenarioStep("high_cpu", 30, severity="medium", description="CPU remains elevated — sustained pressure"),
            ScenarioStep("high_cpu", 60, severity="high", description="CPU still high — triggers high_cpu alert"),
            ScenarioStep("high_memory", 90, severity="medium", description="Memory usage climbs to 92%"),
            ScenarioStep("high_memory", 120, severity="high", description="Memory exhaustion — triggers high_memory alert"),
            ScenarioStep("high_disk", 150, severity="high", description="Disk usage reaches 88%"),
            ScenarioStep("service_failure", 180, severity="critical", description="Critical service crashes due to resource exhaustion"),
            ScenarioStep("agent_disconnect", 240, severity="critical", description="Agent loses connectivity — host goes offline"),
        ],
    ),
    # ── Scenario 3: SOC Resilience ──
    "soc_resilience": ScenarioDef(
        id="soc_resilience",
        name="SOC Resilience",
        summary="Agent buffering during backend outage: events accumulate locally, then replay after recovery",
        difficulty="advanced",
        expected_alerts=["failed_logins"],
        expected_outcomes=["buffered_replay", "deduplication"],
        steps=[
            # Phase 1: Normal operation — events flowing
            ScenarioStep("ssh_login_failure", 0, description="Normal event — agent connected"),
            ScenarioStep("ssh_login_failure", 10, description="Normal event — agent connected"),
            # Phase 2: Backend unavailable — events buffered locally
            ScenarioStep("ssh_login_failure", 30, description="[BUFFERED] Backend unavailable — event queued in SQLite"),
            ScenarioStep("ssh_login_failure", 40, description="[BUFFERED] Still offline — event queued"),
            ScenarioStep("ssh_login_failure", 50, description="[BUFFERED] Buffer accumulating"),
            ScenarioStep("high_cpu", 55, severity="medium", description="[BUFFERED] Metric captured while offline"),
            ScenarioStep("high_memory", 60, severity="medium", description="[BUFFERED] Memory spike captured offline"),
            # Phase 3: Backend recovered — buffered events replayed
            ScenarioStep("ssh_login_failure", 90, description="[REPLAY] Backend restored — buffered events ingested"),
            ScenarioStep("ssh_login_failure", 95, description="[REPLAY] Replay continues — deduplication active"),
            ScenarioStep("ssh_login_success", 110, description="New event after recovery — normal flow resumed"),
        ],
    ),
    # ── Legacy scenarios (kept for backward compatibility) ──
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
            "severity": step.severity,
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
