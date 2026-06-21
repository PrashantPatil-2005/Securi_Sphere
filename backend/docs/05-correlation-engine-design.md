# 5. Correlation Engine Design

## Overview

The correlation engine detects multi-event attack patterns within time windows and produces alerts with confidence scores. It follows an extensible rule-matcher framework comparable to Sigma/QRadar CRE logic (simplified).

---

## Architecture

```
Events (time window)
       │
       ▼
┌──────────────────┐
│ Rule Loader      │ ← correlation_rules table
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Matcher Factory  │
│ ├─ Sequence      │  Ordered event patterns
│ └─ Co-Occurrence │  Unordered co-presence
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Confidence Score │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Alert + Result   │ → alerts, correlation_results
└──────────────────┘
```

---

## Rule Schema

```json
{
  "name": "Brute Force Success",
  "description": "Failed logins followed by successful login",
  "event_sequence": ["ssh_login_failure", "ssh_login_success"],
  "window_minutes": 15,
  "min_occurrences": {"ssh_login_failure": 3},
  "severity": "critical",
  "confidence_base": 0.80,
  "enabled": true,
  "is_system": true
}
```

---

## Built-in Rules

| Rule | Pattern | Severity |
|------|---------|------------|
| **Brute Force Success** | failed_login×3 → login_success | critical |
| **Privilege Escalation Suspicion** | failed_login×2 → sudo_usage | high |
| **Brute Force to Priv Esc** | failed×3 → success → sudo | critical |
| **Potential Host Compromise** | service_stop + agent_disconnect | critical |
| **Service Failure Chain** | service_failure×3 | high |

---

## Matcher Types

### SequenceMatcher
- Events must occur in defined order within window
- Supports `min_occurrences` for repeated event types
- Example: `[A, A, A, B, C]` matches sequence `[A, B, C]` with min A=3

### CoOccurrenceMatcher
- All event types must appear in window (order irrelevant)
- Used for: service_stop + agent_disconnect
- Identified by `[co_occurrence]` prefix in rule description

---

## Confidence Scoring

```
base = confidence_base × 100
+ 15 if sudo + login_success both present
+ 10 if ≥5 failed logins
+ 10 if event span < 10 minutes
= min(total, 100)
```

---

## Deduplication

One correlation result per (rule_id, host_id, window) — prevents alert storms.

---

## Extensibility

Add new matchers by implementing `CorrelationRuleMatcher`:

```python
class ThresholdMatcher(CorrelationRuleMatcher):
    """N events of same type in window."""
    def matches(self, events, rule): ...
    def score(self, events, rule): ...
```

Register in `MATCHERS` dict. Add rules via API or seed data.

---

## Performance

- Query events: `WHERE host_id = ? AND timestamp >= now() - max_window`
- Index: `(host_id, timestamp)` — covered
- At scale: pre-filter event types using GIN index on event_type array per host cache

---

## Future: Cross-Host Correlation

Phase 2 rules matching on `source_ip` across hosts:
- Same IP failing login on 5+ hosts → distributed brute force
- Requires join on `events.source_ip` with window aggregation

See diagram: [correlation-engine.mmd](./diagrams/correlation-engine.mmd)
