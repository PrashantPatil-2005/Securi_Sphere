# Compliance Report Templates

SOC 2 Type II and ISO/IEC 27001:2022 control assessments with evidence pulled from your Securi deployment.

## Frameworks

| ID | Framework | Controls |
|----|-----------|----------|
| `soc2` | SOC 2 Type II (subset) | 8 Trust Services Criteria |
| `iso27001` | ISO/IEC 27001:2022 (subset) | 7 Annex A controls |

Each control is evaluated as **pass**, **partial**, or **fail** based on live platform evidence.

## Evidence sources

- RBAC roles and active users
- OIDC/SSO configuration
- Audit log volume and admin actions
- Agent coverage and event ingestion
- Detection rules, alerts, resolution rate
- Incidents, offenses, UEBA anomalies
- Retention policy and playbooks

## API

```
GET /api/v1/reports/compliance/templates
GET /api/v1/reports/compliance?framework=soc2&report_type=monthly&format=pdf
GET /api/v1/reports/compliance?framework=iso27001&format=json
```

Parameters:
- `framework`: `soc2` | `iso27001`
- `report_type`: `daily` | `weekly` | `monthly` (default `monthly`)
- `format`: `pdf` | `json`

## UI

**Reports** → **Compliance assessment** — pick framework and download PDF or preview JSON.

## Score

```
compliance_score = 100 × (pass + 0.5 × partial) / total_controls
```

## Notes

These are **operational readiness** assessments mapped to common auditor questions — not a substitute for a formal SOC 2 or ISO certification audit. Supplement with organizational policies, vendor contracts, and manual control testing.

Generated reports are stored in `generated_reports` as `compliance_{framework}_{period}`.
