# Notification Rules

Per-user rules for when Securi delivers outbound notifications (email, Slack, Telegram).

## How it works

1. Configure **delivery channels** in Settings → Notifications (email address, Slack webhook, etc.).
2. Create **rules** specifying trigger, minimum severity, and which channels to use.
3. When an alert or offense matches, only users with matching rules receive notifications.

If **no rules exist** in the system, the legacy behavior applies: all users with channels enabled receive high/critical alerts.

## Triggers

| Trigger | Fires when |
|---------|------------|
| `alert_created` | New deduplicated alert |
| `offense_created` | New correlated offense (high/critical notify job) |

## Severity filter

Rule fires when event severity **≥** `min_severity` (low → critical).

## API

```
GET    /api/v1/notifications/rules
POST   /api/v1/notifications/rules
PATCH  /api/v1/notifications/rules/{id}
DELETE /api/v1/notifications/rules/{id}
POST   /api/v1/notifications/rules/{id}/test
```

## UI

**Settings → Notifications** — delivery channels + notification rules panels.

### Delivery test

Send a test message without waiting for a real alert:

```
POST /api/v1/notifications/settings/test
```

Body includes `channels` plus optional unsaved form values (`email_address`, `slack_webhook_url`, etc.) so you can test before saving.

Per-channel **Test** buttons and **Test all enabled** are on the delivery settings panel.

## Migration

```bash
cd backend && alembic upgrade head
```

Revision `012_notification_rules`.
