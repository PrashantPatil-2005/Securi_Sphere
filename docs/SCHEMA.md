# Database Schema

PostgreSQL with UUID primary keys. Tables created automatically on backend startup.

## Tables

- roles - admin, analyst, viewer (seeded)
- users - email, hashed password, role
- refresh_tokens - JWT refresh token hashes
- password_reset_tokens - one-time reset tokens
- audit_logs - user activity tracking
- hosts - monitored systems (status: online/offline/warning/critical)
- enrollment_tokens - one-time agent enrollment
- events - security/system events (JSONB metadata)
- metrics - 30-second resource samples
- alert_rules - static detection rules (seeded)
- alerts - generated alerts (open/resolved)
- notification_settings - email/telegram preferences

## Retention

Events and metrics older than 90 days are deleted daily at 2 AM.


## Advanced tables (v1.1)

- mitre_techniques - seeded ATT&CK technique catalog
- correlation_rules - multi-event sequence rules (seeded)
- correlation_results - matched correlation events with confidence
- attack_timelines - reconstructed attack chains per host
- host_threat_scores - threat and health scores per host
- incidents, incident_alerts, incident_notes - incident workflow

## Extended columns

- hosts: agent_hash, agent_version, agent_hash_changed_at, health_status
- events: mitre_technique_id, mitre_tactic
- alerts: mitre_technique_id, mitre_tactic, confidence
- enrollment_tokens: revoked_at, revoked_by, label
