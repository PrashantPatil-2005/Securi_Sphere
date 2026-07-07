# Host risk score trends

Track how host threat scores change over time on **Analytics** and in the host risk drawer.

## API

```
GET /api/v1/siem/risk-score-trends?preset=7d
GET /api/v1/siem/risk-score-trends?preset=24h&host_id={uuid}
```

Response:

- `fleet_average` — bucketed average risk/health across all hosts (hourly if range ≤ 72h, else daily)
- `series` — per-host score points with `delta` (end − start in range)
- `top_movers` — hosts with the largest risk increases

Existing per-host detail: `GET /api/v1/hosts/{id}/risk` (factor breakdown + history).

## UI

- **Analytics → Host risk score trends** — multi-line chart, host focus filter, top movers
- **Top risky hosts** — click a host to open the risk drawer
- **Host risk drawer** — line chart for risk vs health history

## Data source

Scores are recorded in `host_risk_scores` when threat scores change by ≥5 points or at most once per hour (`threat_score.calculate_host_scores`).
