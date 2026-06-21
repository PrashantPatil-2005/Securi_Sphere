# 4. Database Optimization Plan

## Schema Overview (30 Tables)

### Core Entities
- `users`, `roles`, `refresh_tokens`, `user_sessions`, `password_reset_tokens`
- `hosts`, `enrollment_tokens`, `agent_request_nonces`
- `events`, `metrics`
- `alert_rules`, `alerts`
- `correlation_rules`, `correlation_results`
- `offenses`, `offense_events`
- `host_threat_scores`, `host_risk_scores`
- `attack_timelines`, `incidents`, `incident_notes`, `incident_alerts`
- `mitre_techniques`, `mitre_mappings`
- `audit_logs`, `notification_settings`
- `saved_searches`, `generated_reports`
- `analytics_daily_stats`

---

## Normalization Assessment

### Well Normalized
- Users/Roles — proper FK relationship
- Alerts → AlertRules — FK with nullable rule_id for correlation alerts
- OffenseEvents — junction table for offense↔event/alert

### Denormalization (Intentional)
- `events.normalized_event` JSONB — search/display cache
- `events.source_ip`, `events.username` — extracted for indexed queries
- `offenses.timeline`, `related_users` — read-optimized offense view
- `analytics_daily_stats` — OLAP pre-aggregation

### Issues Fixed
- Events stored only raw logs → now have `normalized_event` + extracted fields
- Offenses lacked related entity tracking → added JSONB arrays

---

## Missing Constraints (Added)

```sql
ALTER TABLE events ADD CONSTRAINT chk_events_severity
  CHECK (severity IN ('info','low','medium','high','critical'));

ALTER TABLE alerts ADD CONSTRAINT chk_alerts_status
  CHECK (status IN ('open','investigating','resolved','closed'));

ALTER TABLE host_threat_scores ADD CONSTRAINT chk_threat_score_range
  CHECK (score >= 0 AND score <= 100);
```

### Recommended Additional Constraints

```sql
-- Prevent orphan events
ALTER TABLE events ALTER COLUMN host_id SET NOT NULL;

-- Offense must have at least one link (application-enforced)
ALTER TABLE offense_events ADD CONSTRAINT chk_offense_link
  CHECK (event_id IS NOT NULL OR alert_id IS NOT NULL);

-- Unique offense-event pairs
CREATE UNIQUE INDEX uq_offense_event ON offense_events (offense_id, event_id)
  WHERE event_id IS NOT NULL;
CREATE UNIQUE INDEX uq_offense_alert ON offense_events (offense_id, alert_id)
  WHERE alert_id IS NOT NULL;
```

---

## Index Strategy

### Events (Hot Table)

| Index | Purpose | Status |
|-------|---------|--------|
| `(timestamp DESC, host_id)` | Time-range queries per host | ✓ |
| `(event_type, timestamp DESC)` | Type-filtered search | ✓ |
| `(host_id, severity)` | Dashboard filters | ✓ |
| `(username)` | User-centric search | ✓ Added |
| `(source_ip)` | IP-centric search | ✓ Added |
| `(category)` | Category analytics | ✓ Added |
| GIN `(normalized_event jsonb_path_ops)` | JSON field search | ✓ Added |

### Alerts

| Index | Purpose |
|-------|---------|
| `(created_at DESC, status)` | Alert inbox |
| `(host_id, severity)` | Host alert panel |

### Missing (Recommended)

```sql
-- Partial index for open alerts (most queries)
CREATE INDEX ix_alerts_open ON alerts (created_at DESC)
  WHERE status = 'open';

-- BRIN for time-series append-only events (space-efficient at scale)
CREATE INDEX ix_events_timestamp_brin ON events USING brin (timestamp);
```

---

## Query Optimizations

### Before
```sql
-- SIEM search scanned metadata JSONB
WHERE metadata->>'username' ILIKE '%root%'
```

### After
```sql
-- Uses indexed column with JSONB fallback
WHERE username ILIKE '%root%' OR metadata->>'username' ILIKE '%root%'
```

### N+1 Patterns Found

| Location | Pattern | Fix |
|----------|---------|-----|
| `update_all_threat_scores` | Loop all hosts | Batch query or parallel workers |
| Offense list | No eager load of links | `selectinload(Offense.links)` |
| Event list | Host name per row | JOIN hosts in query_builder |

---

## Partitioning Strategy

### Events Table (Critical at 10M+ rows)

```sql
-- Monthly range partitioning
CREATE TABLE events (
    ...
) PARTITION BY RANGE (timestamp);

CREATE TABLE events_2026_06 PARTITION OF events
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

CREATE TABLE events_2026_07 PARTITION OF events
    FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
```

**Retention integration:** Drop partitions older than `retention_days` instead of DELETE.

### Metrics Table
Same monthly partitioning — high insert rate.

### Audit Logs
Quarterly partitions — lower volume but compliance retention.

---

## Read Replica Routing

| Query Type | Target |
|------------|--------|
| Event search | Read replica |
| Dashboard analytics | `analytics_daily_stats` on replica |
| Alert mutations | Primary |
| Agent ingest | Primary |
| Threat scores (read) | Replica OK (eventual consistency) |

---

## Migration Strategy

**Current:** `migrate_schema()` — additive DDL on startup  
**Target:** Alembic versioned migrations

```
alembic/versions/
├── 001_initial_schema.py
├── 002_event_normalization.py
├── 003_offense_enhancements.py
├── 004_user_sessions.py
└── 005_analytics_daily_stats.py
```

Never use `create_all()` in production after initial deploy.
