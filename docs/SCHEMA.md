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
