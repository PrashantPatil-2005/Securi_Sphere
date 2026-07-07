# Executive PDF Reports

Board- and leadership-ready security summaries with KPIs, MITRE highlights, UEBA status, and auto-generated recommendations.

## Contents

Each executive report includes:

- **Executive summary** — hosts, alerts, events, risk score, offenses, incidents, UEBA anomalies
- **Alert severity breakdown** (period)
- **Top risky hosts**
- **MITRE ATT&amp;CK** technique highlights
- **Authentication threats** — failed login volume and top source IPs
- **Recommendations** — rule-based action items based on current posture

## Download

### UI

**Reports** → **Executive PDF** (weekly default) or standard **Export PDF** on any period.

### API

```
GET /api/v1/reports/executive?report_type=weekly&format=pdf
GET /api/v1/reports/executive?report_type=monthly&format=json
```

`report_type`: `daily` | `weekly` | `monthly`

`format`: `pdf` | `json` (preview data)

The legacy `GET /api/v1/reports/generate?format=pdf` endpoint also uses the executive PDF layout.

## Audit

Generated reports are stored in `generated_reports` with `report_type` prefixed `executive_` (e.g. `executive_weekly`).

## Requirements

- `reportlab` (included in `backend/requirements.txt`)
- Analyst or admin role (Reports page)
