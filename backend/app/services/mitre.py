EVENT_MITRE_MAP = {
    "ssh_login_failure": {"technique_id": "T1110.001", "tactic": "Credential Access", "name": "Brute Force: Password Guessing"},
    "ssh_login_success": {"technique_id": "T1078", "tactic": "Initial Access", "name": "Valid Accounts"},
    "root_login": {"technique_id": "T1078.003", "tactic": "Initial Access", "name": "Valid Accounts: Local Accounts"},
    "sudo_usage": {"technique_id": "T1548.003", "tactic": "Privilege Escalation", "name": "Sudo and Sudo Caching"},
    "service_failure": {"technique_id": "T1489", "tactic": "Impact", "name": "Service Stop"},
    "service_start": {"technique_id": "T1569.002", "tactic": "Execution", "name": "System Services"},
    "service_stop": {"technique_id": "T1489", "tactic": "Impact", "name": "Service Stop"},
}

MITRE_SEED = [
    {"technique_id": "T1110.001", "tactic": "Credential Access", "name": "Brute Force: Password Guessing"},
    {"technique_id": "T1110", "tactic": "Credential Access", "name": "Brute Force"},
    {"technique_id": "T1078", "tactic": "Initial Access", "name": "Valid Accounts"},
    {"technique_id": "T1078.003", "tactic": "Initial Access", "name": "Valid Accounts: Local Accounts"},
    {"technique_id": "T1548.003", "tactic": "Privilege Escalation", "name": "Sudo and Sudo Caching"},
    {"technique_id": "T1489", "tactic": "Impact", "name": "Service Stop"},
    {"technique_id": "T1569.002", "tactic": "Execution", "name": "System Services"},
    {"technique_id": "T1021.004", "tactic": "Lateral Movement", "name": "SSH"},
    {"technique_id": "T1059.004", "tactic": "Execution", "name": "Unix Shell"},
    {"technique_id": "T1082", "tactic": "Discovery", "name": "System Information Discovery"},
    {"technique_id": "T1046", "tactic": "Discovery", "name": "Network Service Discovery"},
    {"technique_id": "T1018", "tactic": "Discovery", "name": "Remote System Discovery"},
    {"technique_id": "T1036", "tactic": "Defense Evasion", "name": "Masquerading"},
    {"technique_id": "T1070.004", "tactic": "Defense Evasion", "name": "Indicator Removal: File Deletion"},
    {"technique_id": "T1053.003", "tactic": "Persistence", "name": "Cron"},
    {"technique_id": "T1543.002", "tactic": "Persistence", "name": "Systemd Service"},
    {"technique_id": "T1003.008", "tactic": "Credential Access", "name": "OS Credential Dumping: /etc/passwd"},
    {"technique_id": "T1098", "tactic": "Persistence", "name": "Account Manipulation"},
    {"technique_id": "T1136.001", "tactic": "Persistence", "name": "Create Account: Local Account"},
    {"technique_id": "T1027", "tactic": "Defense Evasion", "name": "Obfuscated Files or Information"},
    {"technique_id": "T1496", "tactic": "Impact", "name": "Resource Hijacking"},
    {"technique_id": "T1498", "tactic": "Impact", "name": "Network Denial of Service"},
    {"technique_id": "T1190", "tactic": "Initial Access", "name": "Exploit Public-Facing Application"},
    {"technique_id": "T1133", "tactic": "Persistence", "name": "External Remote Services"},
    {"technique_id": "T1040", "tactic": "Credential Access", "name": "Network Sniffing"},
    {"technique_id": "T1204.002", "tactic": "Execution", "name": "User Execution: Malicious File"},
    {"technique_id": "T1562.001", "tactic": "Defense Evasion", "name": "Disable or Modify Tools"},
]


async def seed_mitre(db) -> None:
    from sqlalchemy import func, select

    from app.models.mitre import MitreTechnique
    from app.models.siem import MitreMapping

    existing_ids = set(
        (await db.execute(select(MitreTechnique.technique_id))).scalars().all()
    )
    for m in MITRE_SEED:
        if m["technique_id"] not in existing_ids:
            db.add(MitreTechnique(**m, description=m["name"]))

    if (await db.execute(select(func.count()).select_from(MitreMapping))).scalar_one() == 0:
        for event_type, mapping in EVENT_MITRE_MAP.items():
            db.add(
                MitreMapping(
                    event_type=event_type,
                    technique_id=mapping["technique_id"],
                    tactic=mapping["tactic"],
                    technique_name=mapping["name"],
                )
            )


def enrich_event(event) -> None:
    mapping = EVENT_MITRE_MAP.get(event.event_type)
    if not mapping:
        return
    event.mitre_technique_id = mapping["technique_id"]
    event.mitre_tactic = mapping["tactic"]
    meta = dict(event.metadata_ or {})
    meta["mitre"] = mapping
    event.metadata_ = meta


def get_matrix_summary(events: list) -> dict:
    summary: dict[str, dict] = {}
    for e in events:
        tid = getattr(e, "mitre_technique_id", None) or EVENT_MITRE_MAP.get(e.event_type, {}).get("technique_id")
        if not tid:
            continue
        if tid not in summary:
            m = EVENT_MITRE_MAP.get(e.event_type, {})
            summary[tid] = {"technique_id": tid, "tactic": m.get("tactic", ""), "name": m.get("name", tid), "count": 0}
        summary[tid]["count"] += 1
    return summary
