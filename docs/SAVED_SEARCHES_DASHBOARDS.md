# Saved searches & custom dashboards

## Saved searches

Per-user SIEM queries on **Search** (SIEM mode).

### API

```
GET    /api/v1/saved-searches
POST   /api/v1/saved-searches
PATCH  /api/v1/saved-searches/{id}
DELETE /api/v1/saved-searches/{id}
POST   /api/v1/saved-searches/{id}/pin-dashboard
```

Fields: `name`, `query`, `alert_enabled`, `interval_minutes` (1–1440).

### Scheduled alerts

When `alert_enabled` is true, the background job (every 5 minutes) runs the SIEM parser on the query over the last `interval_minutes` window. A medium-severity alert is created when matches are found (deduped per interval).

### UI

- **Search → Saved searches** panel: save, rename, delete, toggle alerts, pin to dashboard
- Deep link: `/search?q=event_type:ssh_login_failure&mode=siem`

## Custom dashboards

Per-user widget layout on the home dashboard.

### API

```
GET /api/v1/dashboard/layout
PUT /api/v1/dashboard/layout
```

Body: `{ "widgets": [{ "id": "kpis", "visible": true }, ...] }`

Built-in widget ids: `kpis`, `onboarding`, `timeline`, `risky_hosts`, `attack_timelines`, `live_feed`.

Pinned saved searches use `saved_search:{uuid}`.

### UI

- **Dashboard → Customize** — show/hide/reorder widgets
- **Search → Pin** on a saved search adds a dashboard widget
