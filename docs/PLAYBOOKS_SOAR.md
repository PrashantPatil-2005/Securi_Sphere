# Playbooks / SOAR Webhooks

Automate outbound webhooks when security events occur — integrate with PagerDuty, Slack workflows, Tines, Shuffle, or custom SOAR endpoints.

## Triggers

| Event | When fired |
|-------|------------|
| `alert_created` | New deduplicated alert |
| `offense_created` | New correlated offense |
| `incident_created` | Manual incident or offense promotion |
| `alert_status_changed` | Alert status patch (includes old/new in `context`) |

Optional **min severity** filter applies to alert/offense/incident severity fields.

## Webhook payload

```json
{
  "event": "alert_created",
  "timestamp": "2026-07-07T12:00:00+00:00",
  "resource_type": "alert",
  "resource_id": "uuid",
  "data": {
    "id": "uuid",
    "title": "Brute Force Attempt",
    "severity": "high",
    "status": "open"
  },
  "context": {
    "old_status": "open",
    "new_status": "investigating"
  }
}
```

Test pings use `event: "test"` with playbook metadata.

## Signing

Set an optional **webhook secret**. Securi adds:

```
X-Securi-Signature: HMAC-SHA256(secret, raw_json_body) as hex
```

## UI

**Settings → Playbooks** (admin and analyst)

- Create/edit/enable playbooks
- **Test** sends a sample payload
- **Runs** shows delivery audit (HTTP status, errors)

## API

| Method | Path |
|--------|------|
| GET/POST | `/api/v1/playbooks` |
| PATCH/DELETE | `/api/v1/playbooks/{id}` |
| GET | `/api/v1/playbooks/{id}/runs` |
| POST | `/api/v1/playbooks/{id}/test` |

Delete is admin-only. Dispatch runs asynchronously via the job queue.

## Migration

```bash
cd backend && alembic upgrade head
```

Revision `010_playbooks`.

## Example: Slack incoming webhook

1. Create playbook: trigger `alert_created`, min severity `high`
2. Webhook URL: your Slack workflow URL
3. Map `data.title` and `data.severity` in the receiving workflow

## Load tests

k6 smoke (`loadtests/smoke.js`) includes `GET /api/v1/playbooks` in CI.
