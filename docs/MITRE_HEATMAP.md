# MITRE heatmap drill-down

Click any technique cell on **MITRE ATT&CK** to open a side panel with counts, top hosts, and recent alerts/events for the selected time range.

## API

```
GET /api/v1/mitre/techniques/{technique_id}/drilldown?preset=24h
```

Response includes:

- `event_count`, `alert_count`
- `top_hosts` — hosts with the most matching events
- `recent_events`, `recent_alerts` — last 10 of each

Event matching uses the same logic as the heatmap: explicit `mitre_technique_id` on events **or** mapped `event_type` from `EVENT_MITRE_MAP`.

## Deep links

- Matrix: `/mitre?technique=T1110.001`
- Filtered lists: `/events?mitre_technique_id=T1110.001&preset=24h`, `/alerts?mitre_technique_id=T1110.001&preset=24h`

## Query filters

`mitre_technique_id` is supported on:

- `GET /api/v1/events`
- `GET /api/v1/alerts`
