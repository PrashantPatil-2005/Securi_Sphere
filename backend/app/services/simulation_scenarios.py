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
    category: str = "authentication"
    required_telemetry: list[str] = field(default_factory=list)
    safety_constraints: list[str] = field(default_factory=list)
    live_instructions: str | None = None  # for Live Linux Lab mode
    notes: str | None = None  # documentation field


SCENARIO_DEFS: dict[str, ScenarioDef] = {
    # ── Scenario 1: Brute Force Attack (Scenario A from requirements) ──
    "brute_force_attack": ScenarioDef(
        id="brute_force_attack",
        name="Brute Force Attack",
        summary="Repeated SSH authentication failures followed by successful login and privilege escalation",
        difficulty="intermediate",
        category="authentication",
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
            ScenarioStep("ssh_login_failure", 85, description="Ninth failed attempt"),
            ScenarioStep("ssh_login_failure", 95, description="Tenth failed attempt — triggers brute_force alert"),
            ScenarioStep("ssh_login_success", 110, description="Attacker successfully authenticates"),
            ScenarioStep("sudo_usage", 140, description="Attacker escalates to root via sudo"),
            ScenarioStep("service_failure", 170, description="Attacker causes service disruption"),
        ],
        required_telemetry=["auth.log", "journald"],
        safety_constraints=["Only against enrolled lab host", "Max 10 failure attempts per run"],
        live_instructions="On target lab host: `ssh -o PubkeyAuthentication=no attacker@localhost` with wrong password, 5–10 times within 60 seconds",
    ),

    # ── Scenario 2: Privilege Escalation Monitoring (Scenario B) ──
    "privilege_escalation": ScenarioDef(
        id="privilege_escalation",
        name="Privilege Escalation Monitoring",
        summary="Repeated failed sudo attempts and suspicious privilege-related activity detection",
        difficulty="intermediate",
        category="privilege-escalation",
        expected_alerts=["privilege_escalation", "root_login"],
        expected_outcomes=["offense", "event_evidence", "mitre_mapping"],
        steps=[
            ScenarioStep("sudo_usage", 0, description="First sudo attempt by user"),
            ScenarioStep("sudo_usage", 20, description="Second sudo attempt — failed credentials"),
            ScenarioStep("sudo_usage", 40, description="Third sudo attempt — failed credentials again"),
            ScenarioStep("root_login", 60, description="Successful root login after failed sudo attempts"),
            ScenarioStep("sudo_usage", 80, description="Successful sudo to root — privilege escalation detected"),
        ],
        required_telemetry=["auth.log", "journald"],
        safety_constraints=["Only against enrolled lab host with sudo configured", "No real system modification"],
        live_instructions="On target lab host: Run `sudo -v` followed by `sudo ls` with wrong password 3 times, then successful sudo",
    ),

    # ── Scenario 3: File Integrity Monitoring (Scenario C) ──
    "file_integrity": ScenarioDef(
        id="file_integrity",
        name="File Integrity Monitoring",
        summary="Monitor designated lab directories and canary files for creation, modification, and permission changes",
        difficulty="beginner",
        category="file-integrity",
        expected_alerts=["file_integrity"],
        expected_outcomes=["event_evidence", "file_evidence"],
        steps=[
            ScenarioStep("file_change", 0, description="Create new lab test file"),
            ScenarioStep("file_change", 30, description="Modify existing lab test file content"),
            ScenarioStep("file_change", 60, description="Change file permissions (chmod 644)"),
            ScenarioStep("file_change", 90, description="Delete lab test file"),
        ],
        required_telemetry=["auth.log", "journald"],
        safety_constraints=["Uses designated lab directory only — no system files affected", "Lab directory must exist on target host"],
        live_instructions="On target lab host: Create/Modify/Delete files in /tmp/securi-lab-files/ directory",
    ),

    # ── Scenario 4: Systemd Service & Persistence Monitoring (Scenario D) ──
    "systemd_monitoring": ScenarioDef(
        id="systemd_monitoring",
        name="Systemd Service & Persistence Monitoring",
        summary="Detect unexpected service creation, changes to startup configuration, and suspicious service behavior",
        difficulty="intermediate",
        category="systemd-persistence",
        expected_alerts=["service_stop", "service_failure"],
        expected_outcomes=["offense", "attack_timeline", "service_evidence"],
        steps=[
            ScenarioStep("service_stop", 0, description="Critical system service stopped unexpectedly"),
            ScenarioStep("service_start", 20, description="Service restarted — potential persistence mechanism"),
            ScenarioStep("service_failure", 40, description="Service crashed on restart — detection triggers service_failure alert"),
        ],
        required_telemetry=["auth.log", "journald"],
        safety_constraints=["Only stops/starts services the agent can safely manage", "No services critical to host operation"],
        live_instructions="On target lab host: `systemctl stop sshd`, wait 20s, `systemctl start sshd`; or use non-critical service like `systemctl restart cron`",
    ),

    # ── Scenario 5: Network Reconnaissance (Scenario E) ──
    "network_reconnaissance": ScenarioDef(
        id="network_reconnaissance",
        name="Network Reconnaissance",
        summary="Detect unusual connection attempts across multiple destination ports (controlled localhost scenario)",
        difficulty="beginner",
        category="network-recon",
        expected_alerts=["firewall_block"],
        expected_outcomes=["event_evidence", "mitre_mapping"],
        steps=[
            ScenarioStep("network_flow", 0, description="Recon probe — connection attempt to port 22"),
            ScenarioStep("firewall_block", 5, description="Firewall blocked scan to port 22"),
            ScenarioStep("firewall_block", 10, description="Firewall blocked scan to port 80"),
            ScenarioStep("firewall_block", 15, description="Firewall blocked scan to port 443"),
            ScenarioStep("firewall_block", 20, description="Firewall blocked scan to port 3306"),
            ScenarioStep("firewall_block", 25, description="Firewall blocked scan to port 21"),
            ScenarioStep("firewall_block", 30, description="Firewall blocked scan to port 23"),
            ScenarioStep("firewall_block", 35, description="Firewall blocked scan to port 25"),
            ScenarioStep("firewall_block", 40, description="Firewall blocked scan to port 110"),
            ScenarioStep("firewall_block", 45, description="Firewall blocked scan to port 143"),
            ScenarioStep("firewall_block", 50, description="Tenth blocked connection — triggers firewall_block surge alert"),
            ScenarioStep("network_flow", 55, description="Scanner retries after blocks — continued reconnaissance"),
        ],
        required_telemetry=["flow collector configured"],
        safety_constraints=["Limited to localhost or isolated lab VM — no external network scanning", "Requires flow collector configuration on backend"],
        live_instructions="On target lab host (authorized localhost only): run `nc -zv localhost 22-80` or `for p in 21 22 23 25 80 110 143 443 3306 8080; do nc -zv localhost $p; done` — the agent flow collector reports each connection attempt and the port_scan rule fires when distinct ports exceed the threshold",
        notes=(
            "Scenario E exercises firewall_block (synthetic burst) and port_scan "
            "(live flow telemetry). Synthetic mode replays firewall_block events "
            "(expected_alerts lists what the synthetic preset raises). Live lab "
            "mode requires the agent flow collector enabled (flow_collector.enabled "
            "in agent config) so network_flow events carry real src/dst ports that "
            "the port_scan checker aggregates by source IP — live mode additionally "
            "raises the port_scan alert."
        ),
    ),

    # ── Scenario 6: Agent Tampering & Heartbeat Loss (Scenario F) ──
    "agent_tampering": ScenarioDef(
        id="agent_tampering",
        name="Agent Tampering & Heartbeat Loss",
        summary="Monitor agent service state and heartbeat freshness; detect unexpected termination and prolonged heartbeat loss",
        difficulty="intermediate",
        category="agent-health",
        expected_alerts=["agent_offline"],
        expected_outcomes=["host_risk_change", "status_change"],
        steps=[
            ScenarioStep("agent_disconnect", 0, description="Agent service stopped — heartbeat ceases"),
            ScenarioStep("high_cpu", 30, severity="medium", description="Metrics show CPU pressure during agent downtime"),
            ScenarioStep("high_memory", 60, severity="medium", description="Metrics show memory pressure during agent downtime"),
            ScenarioStep("agent_disconnect", 120, description="Host status changes to offline after 90s heartbeat timeout"),
            ScenarioStep("agent_disconnect", 180, description="Agent service restarted — heartbeat re-established"),
        ],
        required_telemetry=["auth.log", "journald", "agent heartbeat"],
        safety_constraints=["Only against enrolled lab host", "Agent restart is reversible and non-destructive"],
        live_instructions="On target lab host: `systemctl stop securi-agent`, wait 90s, `systemctl start securi-agent`",
    ),

    # ── Scenario 7: Host Health Crisis (Scenario G) ──
    "host_health_crisis": ScenarioDef(
        id="host_health_crisis",
        name="Host Health Incident",
        summary="Detect resource pressure and service failures on a compromised host",
        difficulty="beginner",
        category="host-health",
        expected_alerts=["high_cpu", "high_memory", "high_disk", "service_failure"],
        expected_outcomes=["host_risk_change", "status_change"],
        steps=[
            ScenarioStep("high_cpu", 0, severity="medium", description="CPU usage spikes to 95%"),
            ScenarioStep("high_memory", 30, severity="medium", description="Memory usage spikes to 92%"),
            ScenarioStep("high_disk", 60, severity="medium", description="Disk usage exceeds 90%"),
            ScenarioStep("service_failure", 90, description="Critical service stops responding"),
            ScenarioStep("agent_disconnect", 120, description="Agent becomes unresponsive due to resource exhaustion"),
            ScenarioStep("high_cpu", 150, severity="medium", description="CPU usage remains elevated"),
        ],
        required_telemetry=["auth.log", "journald", "metrics"],
        safety_constraints=["Only against enrolled lab host", "No actual service disruption on production"],
        live_instructions="On target lab host: `dd if=/dev/zero of=/tmp/large bs=1M count=1000` to induce pressure, then monitor",
        notes="Scenario G: Host health incident with resource pressure events and agent disconnect",
    ),

# ── Scenario 8: SOC Resilience (Scenario H) ──
    "soc_resilience": ScenarioDef(
        id="soc_resilience",
        name="SOC Resilience",
        summary="Demonstrate buffering and replay concepts with SSH failure and recovery cycles",
        difficulty="advanced",
        category="agent-health",
        expected_alerts=["failed_logins", "ssh_success_after_failures", "high_memory"],
        expected_outcomes=["buffered_replay", "deduplication"],
        steps=[
            ScenarioStep("ssh_login_failure", 0, description="First SSH failure — start of attack cycle"),
            ScenarioStep("high_cpu", 10, severity="medium", description="Resource metric captured during failure"),
            ScenarioStep("BUFFERED", 20, description="BUFFERED: Event queued during agent instability"),
            ScenarioStep("ssh_login_failure", 25, description="Second SSH failure — same cycle"),
            ScenarioStep("ssh_login_success", 30, description="Recovery: Successful login after failure"),
            ScenarioStep("REPLAY", 40, description="REPLAY: Replay of initial failure for correlation"),
            ScenarioStep("ssh_login_failure", 50, description="Second attack cycle — SSH failure again"),
            ScenarioStep("high_memory", 60, severity="medium", description="Resource metric captured during failure"),
            ScenarioStep("BUFFERED", 70, description="BUFFERED: Second event queued during instability"),
            ScenarioStep("ssh_login_failure", 75, description="Fourth SSH failure — same cycle"),
            ScenarioStep("ssh_login_success", 80, description="Recovery: Successful login after second failure"),
            ScenarioStep("REPLAY", 90, description="REPLAY: Replay of second failure for correlation"),
            ScenarioStep("ssh_login_failure", 100, description="Third attack cycle — SSH failure"),
            ScenarioStep("BUFFERED", 110, description="BUFFERED: Third event queued during instability"),
            ScenarioStep("ssh_login_success", 120, description="Recovery: Successful login after third failure"),
            ScenarioStep("REPLAY", 130, description="REPLAY: Replay of third failure for correlation"),
        ],
        required_telemetry=["auth.log", "journald"],
        safety_constraints=["Only against enrolled lab host", "No real credential disclosure"],
        live_instructions="On target lab host: Repeat `ssh -o PubkeyAuthentication=no baduser@localhost badpass` 3 times with 10s intervals",
        notes="Scenario H: SOC resilience with buffered/replay event phases demonstrating deduplication and correlation",
    ),

    # ── Scenario 9: Authentication Anomaly ─────────────────────────────
    "auth_anomaly": ScenarioDef(
        id="auth_anomaly",
        name="Authentication Anomaly",
        summary="A bounded synthetic authentication-failure sequence processed through the detection pipeline, demonstrating alert generation and MITRE ATT&CK mapping.",
        difficulty="beginner",
        category="authentication",
        expected_alerts=["failed_logins", "ssh_success_after_failures"],
        expected_outcomes=["alert", "mitre_mapping"],
        steps=[
            ScenarioStep("ssh_login_failure", 0, description="First SSH login failure"),
            ScenarioStep("ssh_login_failure", 10, description="Second SSH login failure"),
            ScenarioStep("ssh_login_failure", 20, description="Third SSH login failure"),
            ScenarioStep("ssh_login_failure", 30, description="Fourth SSH login failure"),
            ScenarioStep("ssh_login_failure", 40, description="Fifth SSH login failure — failed_logins threshold reached"),
            ScenarioStep("ssh_login_success", 50, description="Successful SSH login after repeated failures"),
        ],
        required_telemetry=["auth.log", "journald"],
        safety_constraints=["Synthetic sequence only — no real system compromise", "Controlled failure count (×5)"],
        live_instructions=None,
        notes="Scenario I: Authentication anomaly demo for guided SIEM center. Exercises FailedLoginsChecker and SuccessfulSSHAfterFailuresChecker through the detection pipeline.",
    ),

    # ── Scenario 10: Multi-Stage Incident ────────────────────────────
    "multi_stage": ScenarioDef(
        id="multi_stage",
        name="Multi-Stage Incident",
        summary="A clearly labeled synthetic sequence containing multiple related security events, exercising the real correlation engine and displaying the resulting incident with chronological timeline and correlated evidence.",
        difficulty="intermediate",
        category="multi-stage",
        expected_alerts=["brute_force", "failed_logins", "privilege_escalation"],
        expected_outcomes=["offense", "attack_timeline", "correlated_evidence"],
        steps=[
            ScenarioStep("ssh_login_failure", 0, description="First SSH login failure"),
            ScenarioStep("ssh_login_failure", 10, description="Second SSH login failure"),
            ScenarioStep("ssh_login_failure", 20, description="Third SSH login failure"),
            ScenarioStep("ssh_login_failure", 30, description="Fourth SSH login failure"),
            ScenarioStep("ssh_login_failure", 40, description="Fifth SSH login failure — failed_logins threshold reached"),
            ScenarioStep("ssh_login_failure", 50, description="Sixth SSH login failure"),
            ScenarioStep("ssh_login_failure", 60, description="Seventh SSH login failure"),
            ScenarioStep("ssh_login_failure", 70, description="Eighth SSH login failure"),
            ScenarioStep("ssh_login_failure", 80, description="Ninth SSH login failure"),
            ScenarioStep("ssh_login_failure", 90, description="Tenth SSH login failure — brute_force threshold reached"),
            ScenarioStep("service_start", 100, description="Service start event — possible persistence"),
            ScenarioStep("sudo_usage", 110, description="First sudo invocation after access"),
            ScenarioStep("sudo_usage", 120, description="Second sudo invocation — privilege escalation threshold approaching"),
            ScenarioStep("sudo_usage", 130, description="Third sudo invocation — privilege_escalation threshold reached"),
        ],
        required_telemetry=["auth.log", "journald", "metrics"],
        safety_constraints=["Synthetic sequence only — no real system compromise"],
        live_instructions=None,
        notes="Scenario J: Multi-stage incident demo exercising the correlation engine with related event sequence.",
    ),

    # ── Scenario 11: Agent Resilience ────────────────────────────────
    "agent_resilience": ScenarioDef(
        id="agent_resilience",
        name="Agent Resilience",
        summary="Demonstrates buffering, interrupted connectivity, retry behavior, and recovery using a controlled test harness with the actual agent buffer implementation. Does not interrupt a production agent or backend.",
        difficulty="advanced",
        category="agent-health",
        expected_alerts=["agent_offline"],
        expected_outcomes=["buffered_replay", "deduplication", "recovery"],
        steps=[
            ScenarioStep("agent_disconnect", 0, description="Agent disconnects from backend"),
            ScenarioStep("high_cpu", 10, severity="medium", description="Resource metric: high CPU"),
            ScenarioStep("high_memory", 20, severity="medium", description="Resource metric: high memory"),
            ScenarioStep("BUFFERED", 30, description="BUFFERED: Event queued during agent instability"),
            ScenarioStep("agent_reconnect", 50, description="Agent reconnects to backend"),
            ScenarioStep("high_cpu", 60, severity="medium", description="Resource metric: CPU normalizing"),
            ScenarioStep("high_memory", 70, severity="medium", description="Resource metric: memory normalizing"),
            ScenarioStep("REPLAY", 80, description="REPLAY: Replay of initial failure for correlation"),
            ScenarioStep("ssh_login_failure", 90, description="SSH failure after recovery"),
            ScenarioStep("BUFFERED", 100, description="BUFFERED: Second event queued"),
            ScenarioStep("agent_disconnect", 110, description="Agent disconnects again"),
            ScenarioStep("agent_reconnect", 130, description="Agent reconnects — recovery complete"),
        ],
        required_telemetry=["auth.log", "journald"],
        safety_constraints=["Synthetic test harness only — no live agent disruption", "Buffer operations are deterministic and reversible"],
        live_instructions=None,
        notes="Scenario K: Agent resilience demo using the real buffer module (enqueue, flush, dequeue_all, purge_stale).",
    ),

    # ── Legacy scenarios (kept for backward compatibility) ──
    "multi_stage_attack": ScenarioDef(
        id="multi_stage_attack",
        name="Multi-Stage Attack",
        summary="Brute force  access  sudo  root  C2 flow  service impact",
        difficulty="advanced",
        expected_alerts=[
            "failed_logins",
            "brute_force",
            "ssh_success_after_failures",
            "privilege_escalation",
            "root_login",
            "service_failure",
        ],
        expected_outcomes=["offense", "attack_timeline"],
        steps=[
            ScenarioStep("ssh_login_failure", 0),
            ScenarioStep("ssh_login_failure", 20),
            ScenarioStep("ssh_login_failure", 40),
            ScenarioStep("ssh_login_failure", 60),
            ScenarioStep("ssh_login_failure", 80),
            ScenarioStep("ssh_login_failure", 100),
            ScenarioStep("ssh_login_failure", 120),
            ScenarioStep("ssh_login_failure", 140),
            ScenarioStep("ssh_login_failure", 160),
            ScenarioStep("ssh_login_failure", 180),
            ScenarioStep("ssh_login_success", 200),
            ScenarioStep("sudo_usage", 230),
            ScenarioStep("sudo_usage", 245),
            ScenarioStep("sudo_usage", 260),
            ScenarioStep("root_login", 275),
            ScenarioStep("network_flow", 290),
            ScenarioStep("service_failure", 310),
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
            ScenarioStep("ssh_login_failure", 20),
            ScenarioStep("ssh_login_failure", 40),
            ScenarioStep("ssh_login_failure", 60),
            ScenarioStep("ssh_login_failure", 80),
            ScenarioStep("ssh_login_failure", 100),
            ScenarioStep("ssh_login_failure", 120),
            ScenarioStep("ssh_login_failure", 140),
            ScenarioStep("ssh_login_failure", 160),
            ScenarioStep("ssh_login_failure", 180),
            ScenarioStep("ssh_login_success", 200),
            ScenarioStep("sudo_usage", 230),
        ],
    ),
    "brute_force_only": ScenarioDef(
        id="brute_force_only",
        name="Brute Force Only",
        summary="Ten consecutive SSH login failures with no successful access",
        difficulty="beginner",
        expected_alerts=["brute_force", "failed_logins"],
        expected_outcomes=["offense"],
        steps=[ScenarioStep("ssh_login_failure", i * 15) for i in range(10)],
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
        "category": scenario.category,
        "expected_alerts": scenario.expected_alerts,
        "expected_outcomes": scenario.expected_outcomes,
    }


def list_scenarios_api() -> list[dict]:
    return [scenario_to_api(s) for s in SCENARIO_DEFS.values()]
