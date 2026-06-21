# 7. Threat Scoring Design

## Overview

Per-host risk score (0–100) combining security signals. Higher score = higher risk. Historical trends stored for dashboard charts.

---

## Score Formula

```
risk_score = min(sum(factors), 100)
health_score = 100 - risk_score
```

### Factor Weights

| Factor | Weight | Source |
|--------|--------|--------|
| Failed logins (1h) | +3 each, max 25 | events WHERE ssh_login_failure |
| Service failures (1h) | +5 each, max 15 | events WHERE service_failure |
| Critical alerts (open) | +15 each, max 30 | alerts |
| High alerts (open) | +8 each, max 15 | alerts |
| High-severity events (1h) | +4 each, max 15 | events severity high/critical |
| Open offenses | +10 each, max 20 | offenses status open/investigating |
| Agent offline | +10 | host.status offline/critical |
| CPU > 90% | +10 | latest metric |
| Memory > 90% | +10 | latest metric |
| Disk > 85% | +10 | latest metric |

---

## Score Interpretation

| Range | health_status | Label |
|-------|---------------|-------|
| 0–39 | healthy | Low risk |
| 40–69 | warning | Elevated |
| 70–100 | critical | High risk |

---

## Historical Tracking

**Table:** `host_risk_scores` (HostRiskHistory)

Recorded when:
- First score for host
- ≥1 hour since last record
- Score changed by ≥5 points

```json
{
  "host_id": "...",
  "risk_score": 65,
  "health_score": 35,
  "factors": {"failed_logins": 15, "critical_alerts": 30, ...},
  "recorded_at": "2026-06-21T12:00:00Z"
}
```

---

## Computation Schedule

| Trigger | Scope |
|---------|-------|
| Event ingestion (async pipeline) | Single host |
| Metric ingestion | Single host |
| Status job (30s) | All hosts |

---

## API

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/threat-scores` | Ranked host scores |
| `GET /api/v1/siem/host-risk?host_id=` | Single host + history |
| `GET /api/v1/siem/top-risky-hosts` | Top N by score |

---

## Future: ML-Based Scoring

Phase 3: Replace weighted sum with:
- Baseline deviation (z-score per host)
- Peer group comparison
- MITRE technique density weighting
- User behavior analytics (UBA) for username anomalies

---

## Tuning

Factors stored in JSONB — adjustable without schema change. Admin UI for weight configuration recommended.
