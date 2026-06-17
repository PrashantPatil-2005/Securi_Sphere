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
]


async def seed_mitre(db) -> None:
    from sqlalchemy import func, select

    from app.models.mitre import MitreTechnique

    if (await db.execute(select(func.count()).select_from(MitreTechnique))).scalar_one() > 0:
        return
    for m in MITRE_SEED:
        db.add(MitreTechnique(**m, description=m["name"]))


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
