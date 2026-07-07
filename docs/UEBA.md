# UEBA — Baseline Anomaly Detection

User and Entity Behavior Analytics compares recent activity against rolling **7-day daily baselines** and flags statistical spikes (z-score).

## How it works

1. **Daily aggregation** (3 AM cron) stores per-host and per-user counts in `analytics_daily_stats`:
   - `ueba_failed_logins`
   - `ueba_auth_events`
   - `ueba_events_total`

2. **Hourly scan** compares the last **24 hours** (configurable) against the baseline mean, scaled to the observation window.

3. **Anomalies** are stored in `ueba_anomalies` with z-score, severity, and optional linked alert (host spikes only).

## Metrics

| Metric | Host | User |
|--------|------|------|
| `failed_logins` | ✓ | ✓ |
| `auth_events` | ✓ | ✓ |
| `events_total` | ✓ | — |

## Severity

| Z-score | Severity |
|---------|----------|
| ≥ 5 | critical |
| ≥ 4 | high |
| ≥ 3 | medium |
| ≥ threshold | low |

Default threshold: **2.5** (`UEBA_Z_THRESHOLD`).

## UI

**Analytics** page → **UEBA baseline anomalies** panel

- View open anomalies
- Dismiss / resolve
- **Run scan** (manual trigger)
- Links to linked alert or host

## API

| Method | Path |
|--------|------|
| GET | `/api/v1/ueba/summary` |
| GET | `/api/v1/ueba/anomalies` |
| PATCH | `/api/v1/ueba/anomalies/{id}` |
| POST | `/api/v1/ueba/scan` |

## Configuration

```env
UEBA_ENABLED=true
UEBA_Z_THRESHOLD=2.5
UEBA_MIN_OBSERVED=5
UEBA_BASELINE_DAYS=7
UEBA_MIN_BASELINE_SAMPLES=3
UEBA_WINDOW_HOURS=24
UEBA_CREATE_ALERTS=true
UEBA_SCAN_INTERVAL_MINUTES=60
```

## Migration

```bash
cd backend && alembic upgrade head
```

Revision `011_ueba`.

## Requirements

Baselines need at least **3 days** of aggregated stats before anomalies can fire. Run the daily aggregation job or wait for the 3 AM cron after ingest.
