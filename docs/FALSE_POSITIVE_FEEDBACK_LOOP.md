# False-positive feedback loop

Securi now captures analyst feedback on alerts (`false_positive` / `true_positive`) and rolls those signals up per detection rule.

## What it does

- Adds feedback fields on each alert:
  - `feedback_label`
  - `feedback_note`
  - `feedback_at`
  - `feedback_by`
- Tracks per-rule counters:
  - `false_positive_count`
  - `true_positive_count`
  - `feedback_last_updated_at`
- Produces rule-level insights (`false_positive_rate`, recommendation string) for tuning.

When an alert is marked `false_positive`, open/investigating alerts are automatically moved to `closed` to reduce analyst queue noise.

## API

| Method | Path | Role | Description |
|--------|------|------|-------------|
| PATCH | `/api/v1/alerts/{id}/feedback` | admin, analyst | Set feedback label/note |
| GET | `/api/v1/alert-rules/feedback-insights` | admin, analyst | Rule-level FP/TP metrics + recommendations |

### Feedback payload

```json
{
  "label": "false_positive",
  "note": "Expected maintenance noise"
}
```

Valid labels:

- `false_positive`
- `true_positive`

## UI

In **Alerts → Investigation pane**, analysts can click:

- `Mark false positive`
- `Mark true positive`

The selected feedback appears in the alert details card.

## Recommendation logic

`/alert-rules/feedback-insights` computes:

- `feedback_total = false_positive_count + true_positive_count`
- `false_positive_rate = false_positive_count / feedback_total`

Recommendation values:

- `healthy`
- `consider_threshold_increase`
- `consider_disabling_or_refining`

## Migration

Run:

```powershell
cd backend; python -m alembic upgrade head
```

This applies migration `017_false_positive_feedback_loop`.
