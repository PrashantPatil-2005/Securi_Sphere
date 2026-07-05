# SOC Lab — Multi-Stage Attack Investigation

Portfolio walkthrough for SecuriSphere (similar to enterprise SOC lab posts).

## Scenario: `multi_stage_attack`

Run from **Simulation** (admin) or API:

```bash
curl -X POST "http://localhost:8000/api/v1/simulation/run/multi_stage_attack?host_id=HOST_UUID" \
  -H "Authorization: Bearer $TOKEN"
```

### Kill chain simulated

| Stage | Event | MITRE-ish meaning |
|-------|-------|-------------------|
| 1 | `ssh_login_failure` ×4 | Brute force (T1110) |
| 2 | `ssh_login_success` | Initial access |
| 3 | `sudo_usage` | Privilege escalation |
| 4 | `network_flow` → external IP | C2 / exfil pattern |
| 5 | `service_failure` | Impact / disruption |

## Investigation steps (your dashboard)

1. **Alerts** — brute-force rule fires; open investigation pane  
2. **Offenses** — correlated offense grouped; **Promote to incident**  
3. **Search** — `event_type:network_flow` or `source_ip:10.0.0.50`  
4. **Timeline** — attack timeline for host  
5. **MITRE** — map techniques on events page  
6. **IOC** — VirusTotal lookup on `203.0.113.10` (set `VIRUSTOTAL_API_KEY`)  
7. **Incidents** — formal investigation record after promotion  

## Tools mapping (LinkedIn-style)

| Enterprise lab | SecuriSphere |
|----------------|--------------|
| Splunk / Wazuh | SecuriSphere SIEM + search |
| Sysmon / Windows logs | Linux agent events + flows |
| VirusTotal | `/api/v1/ioc/lookup` |
| MITRE ATT&CK | MITRE page + event mapping |
| Timeline analysis | Attack timelines + investigation pane |

## Screenshots checklist

- [ ] Alerts list with investigation pane  
- [ ] Offense detail + Promote button  
- [ ] SIEM search results  
- [ ] MITRE heatmap  
- [ ] Incident after promotion  
- [ ] System Health 3-layer pipeline  

## Sample LinkedIn blurb

> Completed a **multi-stage SOC investigation lab** on SecuriSphere (self-hosted SIEM): brute force → privilege escalation → suspicious outbound flow → service impact. Practiced log correlation, offense grouping, MITRE mapping, IOC validation, and incident promotion in a simulated Linux fleet.

Hashtags: #CyberSecurity #SOCAnalyst #ThreatHunting #SIEM #MITREATTACK #BlueTeam #DFIR
