# 8. Search Architecture

## Current Implementation (v2.0)

Two search modes:

1. **Global Search** — `GET /api/v1/search?q=` — ILIKE across hosts, alerts, events
2. **SIEM Search** — `GET /api/v1/search/siem?q=` — fielded query language

---

## SIEM Query Language

```
host:web01 severity:critical event_type:failed_login username:root source_ip:192.168.1.10 date:last_30_days
```

### Supported Fields

| Field | Aliases | Maps To |
|-------|---------|---------|
| host | hostname | hosts.name/hostname → host_id |
| severity | — | events.severity |
| event_type | type | events.event_type (failed_login → ssh_login_failure) |
| username | user | events.username OR metadata.username |
| source_ip | ip | events.source_ip OR metadata.source_ip |
| status | — | alerts.status |
| date | preset | Time range presets |

### Date Presets

`15m`, `1h`, `24h`, `7d`, `30d`, `90d`, `today`, `last_30_days`

---

## Query Execution Plan

```
Parse query → extract field:value pairs + free text
     │
     ▼
Resolve host name → host_id (indexed lookup)
     │
     ▼
Build SQL clauses on indexed columns first
     │
     ▼
Fallback to JSONB metadata for legacy events
     │
     ▼
Return events + alerts (limit 50 default)
```

---

## Performance Tiers

| Tier | Events | Strategy |
|------|--------|----------|
| <1M | PostgreSQL indexed columns | Current — adequate |
| 1M–50M | PG + BRIN + partitioning | Phase 2 |
| 50M+ | OpenSearch/Elasticsearch | Phase 3 |

---

## OpenSearch Design (Phase 3)

### Index: `securi-events-{YYYY.MM}`

```json
{
  "id": "uuid",
  "timestamp": "2026-06-21T12:00:00Z",
  "host_id": "uuid",
  "host_name": "web01",
  "event_type": "ssh_login_failure",
  "severity": "high",
  "category": "authentication",
  "username": "root",
  "source_ip": "192.168.1.10",
  "description": "...",
  "normalized_event": { ... },
  "raw_event": "..."
}
```

### Ingest Pipeline
PostgreSQL (source of truth) → CDC/Debezium → OpenSearch indexer

### Query Translation
SIEM parser output → OpenSearch Query DSL:
```json
{
  "bool": {
    "must": [
      {"term": {"host_name": "web01"}},
      {"term": {"severity": "critical"}},
      {"range": {"timestamp": {"gte": "now-30d"}}}
    ]
  }
}
```

---

## Saved Searches

Stored in `saved_searches` per user — enables dashboard widgets and scheduled reports.

---

## Search SLA Targets

| Query Type | Target | Index |
|------------|--------|-------|
| Fielded filter | <200ms | B-tree columns |
| Full-text | <500ms | OpenSearch |
| Aggregations | <1s | analytics_daily_stats |

---

## Advanced Features (Roadmap)

- [ ] Boolean operators: `AND`, `OR`, `NOT`
- [ ] Wildcards: `host:web*`
- [ ] Negation: `-severity:info`
- [ ] Parentheses grouping
- [ ] Query history
- [ ] Scheduled search alerts
