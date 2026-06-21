# 6. Offense Engine Design

## Overview

QRadar-style offense grouping consolidates related alerts and events into investigatable offenses. Instead of 100 individual alerts, analysts see 3 offenses with full context.

---

## Grouping Logic

```
New Alert or Security Event
         │
         ▼
┌─────────────────────────┐
│ Find open offense for   │
│ host within 30-min win  │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     │ Found?      │
     ▼             ▼
   Link to      Create new
   existing     offense (#101+)
   offense
     │
     ▼
Update: risk_level, timeline, related_users, counts
```

---

## Offense Model

| Field | Purpose |
|-------|---------|
| `offense_number` | Human-readable ID (101, 102...) |
| `host_id` | Primary host |
| `risk_level` | Max severity across linked items |
| `status` | open → investigating → closed |
| `event_count` | Total linked events + alerts |
| `alert_count` | Linked alerts only |
| `related_hosts` | JSONB array of host UUIDs |
| `related_users` | JSONB array of usernames |
| `timeline` | Chronological activity log |

---

## Timeline Entry Format

```json
{
  "type": "event|alert",
  "id": "uuid",
  "event_type": "ssh_login_failure",
  "severity": "high",
  "username": "root",
  "source_ip": "192.168.1.10",
  "timestamp": "2026-06-21T12:00:00Z"
}
```

---

## Linking Rules

| Source | Linked When |
|--------|-------------|
| Alert | Always via `process_new_alert()` |
| Auth events | ssh_login_*, sudo_usage, root_login |
| System events | service_failure, service_stop, agent_disconnect |

---

## Risk Level Calculation

```
risk_level = MAX(severity of all linked alerts and events)
```

Severity rank: critical > high > medium > low

---

## Example Scenario

**Input:** 47 failed logins, 1 successful login, 1 sudo alert, 3 brute force alerts

**Output:** 1 offense
- offense_number: 1042
- title: "Security activity: ssh_login_failure"
- risk_level: critical
- event_count: 52
- alert_count: 4
- related_users: ["root", "admin"]
- timeline: 52 entries chronologically sorted

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/offenses` | List offenses |
| GET | `/api/v1/offenses/{id}` | Detail with timeline |
| PATCH | `/api/v1/offenses/{id}/status` | Update status |

---

## Future Enhancements

1. **Cross-host offenses** — same source_ip across hosts → single offense
2. **Offense merging** — analyst merges related offenses
3. **Auto-close** — close after 24h with no new activity
4. **Offense rules** — configurable grouping windows per category

See diagram: [offense-engine.mmd](./diagrams/offense-engine.mmd)
