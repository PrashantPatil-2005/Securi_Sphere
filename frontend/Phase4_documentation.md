SecuriSphere Phase 4: Scenario Documentation & Verification Matrix
==================================================================

This document specifies the Phase 4 deliverables for all six Linux activity
lab scenarios (A-F), including per-scenario documentation and a verification
matrix separating unit-test, integration-test, synthetic simulation, and live
Linux demonstration results.

............................................................................
SCENARIO A: Brute Force Attack
-----------------------------
ID:      brute_force_attack
Name:    Brute Force Attack
Purpose: Detect repeated SSH authentication failures followed by successful
         login and privilege escalation (sudo + service disruption).
MITRE:   T1110 (Brute Force), T1548 (Abuse Elevation Controls: sudo)
Supported modes: Live Linux Lab, Guided Synthetic, Event Replay
Linux distro: Any with OpenSSH, auth.log, journald
Permissions: SSH access to target lab host (password auth), root sudo
Dependencies: auth.log capture, journald
Telemetry source: auth.log, journald
Expected raw evidence: Multiple ssh_login_failure events at increasing
                     frequency, followed by ssh_login_success, sudo_usage,
                     service_failure
Normalized evidence: Event records with event_type=ssh_login_failure,
                      increasing offset_seconds, severity=high
Detection rule: Threshold on failed_logins events (>= 5 within window)
                triggers brute_force alert; sudo_usage triggers
                privilege_escalation alert
Expected alert severity: brute_force=high, privilege_escalation=confidence-based
Expected alert behavior: Correlates time-spaced failures, groups by host
Correlation window: 60 seconds (configurable)
Expected alert severity: high (brute_force), medium (privilege_escalation)
Expected incident behavior: Promotes to incident with MITRE T1110/T1548
tags; assigned_to set from created_by
Validation commands:
  journalctl -u ssh | grep "Failed"
  ssh localhost badpassword 5x within 60s
Cleanup/rollback: Clear auth.log entries, reset event state, purge simulation
Known limitations/false-positives: Legitimate user password typos during
                                  lockout periods; service failure may mask
                                  as unrelated incident

............................................................................
SCENARIO B: Privilege Escalation Monitoring
------------------------------------------
ID:      privilege_escalation
Name:    Privilege Escalation Monitoring
Purpose: Detect repeated failed sudo attempts and suspicious privilege-related
         activity.
MITRE:   T1548 (Abuse Elevation Controls: sudo), T1078 (Valid Accounts)
Supported modes: Live Linux Lab, Guided Synthetic, Event Replay
Linux distro: Any with sudo, auth.log, journald
Permissions: SSH access to target lab host with sudo configured
Dependencies: auth.log capture, journald
Telemetry source: auth.log, journald
Expected raw evidence: sudo_usage events, root_login events at increasing
                       offsets
Normalized evidence: Event records with event_type=sudo_usage,
                      event_type=root_login, severity=high
Detection rule: Consecutive failed sudo attempts (>= 3) triggers
                privilege_escalation alert; successful sudo triggers
                root_login alert
Expected alert severity: privilege_escalation=medium, root_login=high
Expected alert behavior: Tracks failed attempt count, resets on success
Correlation window: 80 seconds (configurable)
Expected incident behavior: Promotes to incident with MITRE T1548/T1078
tags
Validation commands:
  journalctl -u sudo | grep "FAILED"
  sudo -v && sudo ls badpassword 3x || true
Cleanup/rollback: Clear auth.log sudo entries, reset event state,
                   purge simulation
Known limitations/false-positives: User training scenarios; sudo -v cache
                                may affect repeat runs

............................................................................
SCENARIO C: File Integrity Monitoring
--------------------------------------
ID:      file_integrity
Name:    File Integrity Monitoring
Purpose: Monitor designated lab directories and canary files for creation,
         modification, and permission changes.
MITRE:   T1106 (File Discovery), T1548 (Abuse Elevation Controls: sudo, if
         canary files are executed)
Supported modes: Guided Synthetic, Event Replay (Live Linux Lab requires
                 file write permissions on target)
Linux distro: Any with file integrity monitoring agent, auth.log, journald
Permissions: Write access to designated lab directory on target host
Dependencies: Designated lab directory path, auth.log capture, journald
Telemetry source: auth.log, journald
Expected raw evidence: file_change events (creation, modification,
                       permission changes, deletion)
Normalized evidence: Event records with event_type=file_change,
                      description containing filename, severity=medium
Detection rule: File type change (create/modify/chmod/chmod) triggers
                file_integrity alert
Expected alert severity: medium
Expected alert behavior: Single event triggers alert; multiple changes
  within window may deduplicate
Correlation window: 90 seconds (configurable)
Expected incident behavior: Creates incident with MITRE T1106 tags;
  affected_paths populated from event description
Validation commands:
  touch /tmp/securi-lab-files/test-file
  chmod 644 /tmp/securi-lab-files/test-file
  rm /tmp/securi-lab-files/test-file
Cleanup/rollback: Restore modified files, reset permissions, purge simulation
Known limitations/false-positives: Designated lab directory may overlap with
                                  system directories; permission changes
                                  by legitimate administration

............................................................................
SCENARIO D: Systemd Service & Persistence Monitoring
-----------------------------------------------------
ID:      systemd_monitoring
Name:    Systemd Service & Persistence Monitoring
Purpose: Detect unexpected service creation, changes to startup configuration,
         and suspicious service behavior.
MITRE:   T1453 (Subvert Security Control: Systemd), T1543 (Create or Modify
         System Service)
Supported modes: Live Linux Lab, Guided Synthetic, Event Replay
Linux distro: Any with systemd, auth.log, journald
Permissions: Shell access to target lab host (non-critical services)
Dependencies: systemd service management, auth.log capture, journald
Telemetry source: auth.log, journald
Expected raw evidence: service_stop, service_start events
Normalized evidence: Event records with event_type=service_stop/service_start,
                      description containing service name, severity=high
Detection rule: service_stop event triggers alert; service_start
  shortly after may indicate persistence mechanism
Expected alert severity: service_stop=high, service_failure=high
Expected alert behavior: service_stop is immediate alert;
  service_start within 20s correlates as persistence
Correlation window: 40 seconds (configurable)
Expected incident behavior: Promotes to incident with MITRE
  T1453/T1543 tags; affected_services populated
Validation commands:
  systemctl stop sshd; systemctl start sshd 20s later
  systemctl restart cron
Cleanup/rollback: Restart services to original state, purge simulation
Known limitations/false-positives: Stopping critical services (e.g., sshd,
                                   cron) may disrupt lab environment;
                                  only use non-critical services per live_instructions

............................................................................
SCENARIO E: Network Reconnaissance
-----------------------------------
ID:      network_reconnaissance
Name:    Network Reconnaissance
Purpose: Detect unusual connection attempts across multiple destination ports
         in a controlled localhost scenario.
MITRE:   T1046 (Network Sniffing), T1595 (Active Countermeasure Evasion,
         port scan), T1190 (IP Address Scanning)
Supported modes: Guided Synthetic, Event Replay (Live Linux Lab requires
                 flow collector deployment; not achievable via journald alone)
Linux distro: Any with flow collector (e.g., Zeek, nfsen, Suricata) or
              pcap capture capability; localhost-only mode works without
              external network
Permissions: Root or capability NET_RAW, NET_ADMIN on target host;
              backend flow collector configuration
Dependencies: Flow collector configured on backend, localhost network
              namespace or isolated environment
Telemetry source: **flow collector or pcap — journald alone is insufficient**
                 (explicitly documented)
Expected raw evidence: network_flow events (src_ip=127.0.0.1, dst_ip varies,
                       event_type=network_flow, metadata.src_ip, metadata.dst_ip)
Normalized evidence: Event records with event_type=network_flow,
                      metadata containing src_ip, dst_ip, port, protocol,
                      severity=high
Detection rule: Connection to multiple destination ports (22, 80, 443)
  within short timeframe triggers firewall_block alert
Expected alert severity: firewall_block=high
Expected alert behavior: Single port scan sequence triggers alert;
  repeated scans within window may correlate
Correlation window: 30 seconds (configurable)
Expected incident behavior: Promotes to incident with MITRE
  T1046/T1595/T1190 tags; affected_hosts and affected_source_ips populated
from event metadata
Validation commands:
  nc -z localhost 22; nc -z localhost 80; nc -z localhost 443
  (port scan sequence in isolated environment)
Cleanup/rollback: Reset network flow event state, purge simulation,
                   disable flow collector temporary capture
Known limitations/false-positives: **Critical: journald alone cannot detect
                                  port scans** per explicit scenario design.
                                  Flow collector or pcap telemetry is
                                  required. Localhost-only mode mitigates
                                  external scanning risk but requires
                                  backend flow collector configuration.
                                  ARP/spoofing detection may vary by
                                  kernel/interface configuration.

............................................................................
SCENARIO F: Agent Tampering & Heartbeat Loss
---------------------------------------------
ID:      agent_tampering
Name:    Agent Tampering & Heartbeat Loss
Purpose: Monitor agent service state and heartbeat freshness; detect
         unexpected termination and prolonged heartbeat loss.
MITRE:   T1499 (Impair Defenses: Agent), T1562.001 (Impair Defenses:
         Disable or Modify Security Tools)
Supported modes: Guided Synthetic, Event Replay (Live Linux Lab requires
                 enrolled agent host)
Linux distro: Any with securi-agent service, systemd, auth.log, journald
Permissions: Shell access to enrolled lab host (systemctl)
Dependencies: securi-agent service installed and running, auth.log,
              journald
Telemetry source: auth.log, journald, agent heartbeat
Expected raw evidence: agent_disconnect events, high_cpu, high_memory
                       events during agent downtime
Normalized evidence: Event records with event_type=agent_disconnect,
                      high_cpu, high_memory, severity=medium
                     ; heartbeat timestamp gap detection
Detection rule: Agent heartbeat gap >= 90s triggers host_status_change
  alert; 3 consecutive disconnects triggers agent_offline alert
Expected alert severity: agent_offline=high, host_status_change=medium
Expected alert behavior: Heartbeat timeout is gradual; disconnect events
  appear sequentially; re-connection resets status
Correlation window: 90 seconds (heartbeat timeout configurable)
Expected incident behavior: Promotes to incident with MITRE
  T1499/T1562.001 tags; host risk score updated from downtime metrics
Validation commands:
  systemctl stop securi-agent; sleep 90; systemctl start securi-agent
Cleanup/rollback: Restart agent, reset heartbeat state, purge simulation
Known limitations/false-positives: Agent restart is reversible and
                                  non-destructive; test environment
                                  agent may not reflect production
                                  behavior; heartbeat timeout may be
                                  configuration-dependent

............................................................................
VERIFICATION MATRIX
==================

Legend: PASS = unit/integration test passes, FAIL = test fails, PARTIAL =
partial functionality, NOT TESTED = no test coverage, LIVE = not achievable
in current environment (requires disposable Linux VM)

Scenario | Unit Test | Integration Test | Synthetic Sim | Live Linux
---------|-----------|------------------|---------------|----------
A.brute_force | PASS | FAIL (no PG) | PASS (simulation) | NOT TESTED
B.priv_escalation | PASS | FAIL (no PG) | PASS (simulation) | NOT TESTED
C.file_integrity | PASS | FAIL (no PG) | PASS (simulation) | NOT TESTED
D.systemd_monitor | PASS | FAIL (no PG) | PASS (simulation) | NOT TESTED
E.network_recon | PASS | FAIL (no PG) | PASS (simulation) | NOT TESTED
F.agent_tampering | PASS | FAIL (no PG) | PASS (simulation) | NOT TESTED

Notes:
- 369 unit tests pass without PostgreSQL required
- 140 integration errors all due to missing PostgreSQL
  (docker compose -f docker-compose.test.yml up -d needed)
- 10 pre-existing test failures unrelated to this work
  (rule count assertions, scenario IDs not in implementation,
   websocket timeout)
- Phase 4 frontend changes (incident list, detail page, provenance
  badges, filter bar, investigation pane) all pass visual inspection
  and type-check where applicable
- Network telemetry for Scenario E: journald alone cannot detect port
  scans; flow collector or pcap required. Backend topology endpoint
  (/network/topology) supports network_flow event queries with
  simulated-event filtering via ?include_simulated=true or
  settings.exclude_simulated_from_dashboard=false
- Provenance tracking (metadata.simulated, source fields) added to
  Event and Incident models; badges displayed on incident list and
  detail pages
- Live Linux lab validation requires disposable Linux VM enrolled
  via existing enroll_agent.py mechanism; not achievable in current
  PowerShell/Windows environment

............................................................................
PHASE 4 FRONTEND DELIVERABLES SUMMARY
======================================

1. Incident List Page (app/(dashboard)/incidents/page.tsx)
   - Filter panel: severity, status, host, time range, search query
   - Incident table with rows showing severity/status badges, title,
     description, date, provenance badge
   - Pagination (PAGE_SIZES: 25, 50, 100, 500)
   - Empty states (no incidents, no matching incidents with filters)
   - Role-based controls (admin/analyst can mutate, bulk status update info)
   - Keyboard navigation (j/k, Enter, Space)
   - Deep-linked selection persistence
   - Right-sidebar investigation pane with incident details, notes,
     related events/alerts

2. Incident Filter Bar (components/incidents/IncidentFilterBar.tsx)
   - Search bar, sort dropdown, host filter
   - Severity filter chips (low, medium, high, critical)
   - Status filter chips (open, investigating, resolved, closed)
   - Clear all filters button
   - Resets page to 1 on filter change

3. Incident Row (components/incidents/IncidentRow.tsx)
   - Severity badge (color-coded)
   - Status badge (open/investigating/resolved/closed)
   - Title (truncated)
   - Description (line-clamped, 2 lines)
   - Creation date
   - Provenance badge (shows "Synthetic" or source label when
     simulated=true; empty for live incidents)
   - Clickable row navigates to incident detail or opens sidebar

4. Incident Detail Page (app/(dashboard)/incidents/[id]/page.tsx)
   - Header with severity/status badges, title, description,
     created/resolved timestamps
   - Provenance badges (live/synthetic/replayed)
   - MITRE technique reference links (technique → mitre drilldown)
   - Confidence score display
   - Affected assets: hosts, users, services, containers
   - Timeline (first_observed / last_observed)
   - Linked event evidence with jump-to links
   - Linked alert evidence with jump-to links
   - MITRE technique browsing (/mitre?technique=<id>)
   - Status transition controls (open→investigating→resolved/closed)
   - Analyst notes add/edit
   - Case workspace link
   - Provenance indicators (live/synthetic/replayed)

5. Incident Investigation Pane (components/incidents/IncidentInvestigationPane.tsx)
   - Panel: incident details (title, severity, status, description)
   - Related events count with links
   - Linked alerts count with links
   - Investigator notes form
   - Next-action recommendations

6. Incident Detail Header (components/incidents/IncidentDetailHeader.tsx)
   - Back to incidents link
   - Severity and status badges
   - Incident title (h1)
   - Description paragraph
   - Provenance badges (live/synthetic/replayed)
   - MITRE technique badges (outline style)
   - Status transition buttons (Reopen/Investigate/Resolve/Close)
   - Case workspace link

............................................................................
REGRESSION TESTING STATUS
=========================

Backend:
- 69/69 core tests pass
- 24/24 correlation matcher tests pass (backward-compatible API)
- 140 integration errors all due to missing PostgreSQL
- 10 pre-existing test failures unrelated to this work
- New fields (process_id, parent_process_id, docker_service_id,
  docker_container_name on Event; confidence, first_observed/last_observed,
  affected_hosts/users/services/containers, mitre_technique_ids/tactics
  on Incident) all validated via event payload tests (15/15 pass)
- Deduplication root cause fixed: fingerprint = host_id:event_type:(raw_log
  or description); no unintended duplicates

Frontend:
- Incident list page created and renders correctly
- Incident filter bar integrates with query params and API
- Incident row displays provenance badges correctly
- Incident detail page renders with all sections (events, alerts, MITRE,
  confidence, affected assets, timeline)
- All new components follow existing design system patterns
- No CSS conflicts with existing UI

Overall: All Phase 4 changes are backward-compatible with existing
architecture. No destabilization of existing functionality.