# Correlation rule editor v2

Visual editor for multi-event correlation rules with validation, templates, and live preview against recent events.

## Rule types

| Type | Matcher | Use case |
|------|---------|----------|
| `sequence` | Ordered steps in a time window | Brute force → success → sudo |
| `co_occurrence` | Unordered set in a window | Service stop + agent disconnect |
| `cross_host` | Same IP/user across hosts | Distributed SSH brute force |

Rule type is stored in the `description` prefix (`[co_occurrence]`, `[cross_host]`) for compatibility with the existing engine.

## UI

**Rules → Correlation** (`/rules`) opens `CorrelationRuleEditor`:

- Template loader (built-in examples)
- Event sequence builder (add / reorder / remove steps)
- Minimum occurrence key-value editor
- **Validate** — checks definition without saving
- **Preview** — dry-run against recent events (per-host or cross-host)
- **Edit** custom rules (system rules: enable/disable and severity only)

Admins create, edit, and delete custom rules. Analysts can validate and preview.

## API

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/api/v1/correlation-rules/meta` | all | Event types, templates, field help |
| POST | `/api/v1/correlation-rules/validate` | admin, analyst | Validate draft |
| POST | `/api/v1/correlation-rules/preview` | admin, analyst | Preview against live data |
| GET | `/api/v1/correlation-rules/{id}` | all | Single rule |
| POST/PATCH/DELETE | `/api/v1/correlation-rules` | admin | CRUD (unchanged) |

### Preview request

```json
{
  "rule_type": "sequence",
  "event_sequence": ["ssh_login_failure", "sudo_usage"],
  "window_minutes": 20,
  "min_occurrences": { "ssh_login_failure": 2 },
  "host_id": null
}
```

Returns `matched`, `matches[]` (per host), or cross-host `event_count` / `confidence`.

## Implementation

- `backend/app/services/correlation/validation.py` — validate, preview, meta
- `frontend/components/rules/CorrelationRuleEditor.tsx` — v2 UI

## Related

- `backend/docs/05-correlation-engine-design.md` — matcher framework
- `docs/GUIDE_DEMO.md` — demo correlation visibility
