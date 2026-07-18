# Database Schema

PostgreSQL with UUID primary keys. Tables created automatically on backend startup via SQLAlchemy models.

## Authentication & Users

| Table | Purpose |
|-------|---------|
| `roles` | Role definitions (admin, analyst, viewer) with JSONB permissions |
| `users` | User accounts with email, hashed password, MFA, lockout tracking |
| `user_sessions` | Active JWT refresh sessions with device/IP tracking |
| `user_invites` | Pending user invitations with token hashes |
| `refresh_tokens` | JWT refresh token hashes |
| `password_reset_tokens` | One-time password reset tokens |

## Hosts & Agents

| Table | Purpose |
|-------|---------|
| `hosts` | Registered Linux hosts with agent version, health status, API key hash |
| `enrollment_tokens` | One-time tokens for agent enrollment |
| `agent_request_nonces` | HMAC nonce tracking (prevents replay attacks) |

## Events & Metrics

| Table | Purpose |
|-------|---------|
| `events` | Normalized security events (17 columns: host, type, severity, MITRE, source_ip, JSONB metadata) |
| `metrics` | System metrics (CPU, memory, disk, network, load average, uptime) |
| `ingest_dedup` | SHA-256 fingerprints for event deduplication |

## Detection & Alerts

| Table | Purpose |
|-------|---------|
| `alert_rules` | Detection rule definitions (threshold, window, severity, feedback counters) |
| `alerts` | Generated alerts with status, feedback labels, resolution tracking |
| `correlation_rules` | Sequence/co-occurrence/cross-host correlation patterns |
| `correlation_results` | Correlation engine output linking events to rules |
| `building_blocks` | Reusable SIEM query components |

## Offenses & Incidents

| Table | Purpose |
|-------|---------|
| `offenses` | QRadar-style grouped alerts with risk level, timeline, related hosts/users |
| `offense_events` | Links offenses to alerts and events |
| `incidents` | Manual incident tracking with assignments |
| `incident_notes` | Incident investigation notes |
| `incident_alerts` | Links incidents to alerts |

## MITRE ATT&CK

| Table | Purpose |
|-------|---------|
| `mitre_techniques` | ATT&CK technique definitions (ID, tactic, name) |
| `mitre_mappings` | Event type → technique mappings |

## Intelligence & Research

| Table | Purpose |
|-------|---------|
| `reference_sets` | IOC lists (IP, domain, hash) with feed sync support |
| `reference_set_entries` | Individual IOC values within reference sets |
| `ueba_anomalies` | User/entity behavior anomalies with z-score detection |
| `attack_timelines` | Reconstructed attack chains with confidence scores |
| `host_risk_scores` | Historical host risk scoring |
| `host_threat_scores` | Current host threat posture |

## Response & Automation

| Table | Purpose |
|-------|---------|
| `playbooks` | Webhook-based automation rules |
| `playbook_runs` | Playbook execution history |
| `notification_rules` | Alert notification routing rules |
| `notification_settings` | User notification preferences (email, Slack, Telegram) |
| `in_app_notifications` | In-app notification feed |
| `in_app_notification_reads` | Read status tracking |
| `maintenance_windows` | Scheduled maintenance suppression |

## Analytics & Reporting

| Table | Purpose |
|-------|---------|
| `analytics_daily_stats` | Pre-aggregated daily metrics |
| `generated_reports` | Cached report generation results |
| `saved_searches` | User-saved search queries with alert capabilities |
| `dashboard_layouts` | Per-user widget layout configurations |
| `telemetry_events` | Frontend usage telemetry |

## Audit

| Table | Purpose |
|-------|---------|
| `audit_logs` | Tamper-evident audit trail with SHA-256 hash chain |

## Simulation

| Table | Purpose |
|-------|---------|
| `simulation_runs` | Attack simulation execution results |

## Total: 34 tables
