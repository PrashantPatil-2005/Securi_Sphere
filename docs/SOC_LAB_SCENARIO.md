# SOC Lab — Multi-Stage Attack Investigation

Portfolio walkthrough for Securi (similar to enterprise SOC lab posts).

## Scenario: `multi_stage_attack`

Run from **Attack Lab** (analyst/admin, sidebar → Lab) or API:

```bash
curl -X POST "http://localhost:8000/api/v1/simulation/run/multi_stage_attack?host_id=HOST_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

Or run `.\scripts\demo-setup.ps1` / `./scripts/demo-setup.sh` — seeds demo user, host, and **multi_stage_attack** automatically.

The Attack Lab page includes a **Guided investigation** bar and SOC checklist. Use **Custom** for ad-hoc chains and **History** for past runs.

### Kill chain simulated

| Stage | Event | MITRE-ish meaning |
|-------|-------|-------------------|
| 1 | `ssh_login_failure` ×4 | Brute force (T1110) |
| 2 | `ssh_login_success` | Initial access |
| 3 | `sudo_usage` | Privilege escalation |
| 4 | `network_flow` → external IP | C2 / exfil pattern |
| 5 | `service_failure` | Impact / disruption |

## Investigation steps (your dashboard)

1. **Alerts** — brute-force rule fires; triage in investigation pane  
2. **Offenses** — correlated offense grouped; **Promote to incident** or **Open Case Workspace**  
3. **Case Workspace** (`/investigation`) — unified alert, offense, host, events, and next actions  
4. **Search** — `event_type:network_flow` or `source_ip:10.0.0.50`  
5. **Timeline** — attack timeline for host  
6. **MITRE** — heatmap + technique drilldown  
7. **IOC** — VirusTotal lookup on host IP in workspace (set `VIRUSTOTAL_API_KEY`)  
8. **Incidents** — formal record after promotion  

## Tools mapping (LinkedIn-style)

| Enterprise lab | Securi |
|----------------|--------------|
| Splunk / Wazuh | Securi SIEM + search |
| Sysmon / Windows logs | Linux agent events + flows |
| VirusTotal | `/api/v1/ioc/lookup` + workspace IOC panel |
| MITRE ATT&CK | MITRE page + event mapping |
| Timeline analysis | Attack timelines + Case Workspace |

## Screenshots checklist

- [ ] Attack Lab guided investigation bar after simulation  
- [ ] Alerts list with investigation pane  
- [ ] Offense detail + Promote / Case Workspace  
- [ ] Case Workspace next-actions rail  
- [ ] SIEM search results  
- [ ] MITRE heatmap + drilldown  
- [ ] Incident after promotion  
- [ ] System Health 3-layer pipeline  

## Sample LinkedIn blurb

> Completed a **multi-stage SOC investigation lab** on Securi (self-hosted SIEM): brute force → privilege escalation → suspicious outbound flow → service impact. Practiced log correlation, offense grouping, Case Workspace triage, MITRE mapping, IOC validation, and incident promotion in a simulated Linux fleet.

Hashtags: #CyberSecurity #SOCAnalyst #ThreatHunting #SIEM #MITREATTACK #BlueTeam #DFIR

## Demo environment tips

- Set `DEMO_MODE=true` for seeded `demo@securi.local` / `Demo1234!` on startup  
- Set `EXCLUDE_SIMULATED_FROM_DASHBOARD=false` so dashboard KPIs reflect simulation data  
- A dismissible banner appears in the top nav when pilot demo mode is active  
