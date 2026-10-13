JURY SCRIPT — 5-Minute Attack Scenario Script
================================================

VIVA VOCE SCRIPT FOR SECURI DEMONSTRATION

Everything quoted below was captured from a real run of
`multi_stage_attack` on the seeded `demo-server` host. Read it as
"what will actually be on screen", not as an aspiration.

[ ] Attack Lab → run **Multi-Stage Attack** (streams for ~10 s)
[ ] Point at the raw log tail: "this is the evidence"
[ ] Switch to Alerts: "the SIEM named it"
[ ] Switch to the offense: "it correlated the kill chain"
[ ] Point at MITRE. Stop. Take questions.

----------------------------------------------------------------------

WHAT THE RUN PRODUCES (verified)
---------------------------------------------------------------

Host:            demo-server (seeded automatically when DEMO_MODE=true)
Scenario:        Multi-Stage Attack — 17 steps, ~5 min of attack time,
                 streamed over ~10 s of wall clock
Events:          17 injected, all carrying `source = simulation`
Alerts:          6
Offense:         1 — titled with the headline alert, 16 events, 6 alerts
Timeline:        1 reconstructed attack chain

The six alerts, exactly as they appear:

  [high]     SSH brute force in progress on demo-server from 198.51.100.23
             rule=failed_logins          MITRE T1110
  [critical] Brute Force Attempt
             rule=brute_force            MITRE T1110
  [critical] Compromised account on demo-server
             rule=ssh_success_after_failures   MITRE T1110
  [critical] Privilege escalation on demo-server
             rule=privilege_escalation   MITRE T1548.003
  [critical] Direct root login on demo-server
             rule=root_login             MITRE T1078.003
  [high]     Service Failure
             rule=service_failure        (no MITRE mapping)

Attacker IP in every injected line: 198.51.100.23
Compromised user in every injected line:  svc_deploy

----------------------------------------------------------------------

SCRIPT (approximately 5 minutes)

---------------------------------------------------------------
0. WHAT WE ARE LOOKING AT (approximately 20 seconds)
---------------------------------------------------------------

TARGET: "Securi is a QRadar-style SIEM. Events come in, detection rules
fire alerts, alerts correlate into offenses, an offense becomes an
incident case. I will walk one attack through all five stages."

ACTION: Open the sidebar so the structure is visible:
Overview → Operations → Intelligence → Lab → Management.

KEY POINT: Every screen we visit is fed by the same pipeline — no
mocked panels, no fabricated charts.

---------------------------------------------------------------
1. THE HOST AND THE EVIDENCE (approximately 1 minute 30 seconds)
---------------------------------------------------------------

ACTION: Go to Attack Lab (`/simulation`). Select target host
`demo-server`, scenario **Multi-Stage Attack**, click **Run simulation**.

TARGET: "Watch it run. It is not a progress bar — the events are being
injected one at a time, and you can see the raw log lines arriving."

[WATCH the raw log tail scroll while the run streams]

[POINT at the tail] "These are the raw log lines as the SIEM receives
them: `Failed password for svc_deploy from 198.51.100.23 ...`, then the
sudo lines, then the root login. Every line is prefixed `[SIMULATED]` —
we label synthetic telemetry so nothing can be mistaken for real data."

[POINT at the live banner] "Up top you can see the kill chain lighting
up as it happens: recon → brute force → initial access → privilege
escalation → impact."

[POINT at the progress banner] "Injecting events → correlating offenses
→ building timelines. That is the real pipeline stages, not a fake
animation."

TALK TRACK: "The evidence is a log line. Everything after this is
interpretation by the platform."

---------------------------------------------------------------
2. SWITCH TO ALERTS — "THE SIEM NAMED IT" (approximately 1 minute)
---------------------------------------------------------------

TARGET: "Raw logs are noise. The rules gave them names."

[ACTION: open the run result / Alerts view]

ACTION: Point at the six alerts in order:

- "SSH brute force in progress on demo-server from 198.51.100.23"
  → 10 failed logins inside 5 minutes — MITRE **T1110**, Brute Force
- "Brute Force Attempt"
  → the same burst classified as a completed brute-force attack
- "Compromised account on demo-server"
  → a successful login immediately after failures — **T1110**
- "Privilege escalation on demo-server"
  → three sudo calls inside 5 minutes — **T1548.003**
- "Direct root login on demo-server"
  → root shell obtained — **T1078.003**
- "Service Failure"
  → the attacker broke something on purpose — impact stage

TALK TRACK:
- "Six detections, five MITRE techniques, one attack."
- "Nothing here was typed in by hand. The rule names matched thresholds:
  10 failures in 5 minutes, 3 sudo in 5 minutes, 1 root login."

KEY MESSAGE: "The SIEM named this attack. It didn't just display logs —
it said *brute force*, *account compromised*, *privilege escalation*,
*root*. That is the difference between a log viewer and a SIEM."

---------------------------------------------------------------
3. SWITCH TO THE OFFENSE — "IT CORRELATED THE KILL CHAIN"
(approximately 1 minute)
---------------------------------------------------------------

TARGET: "Six alerts would still be six disconnected emails. The offense
engine groups them into one story."

[CLICK to Offenses, open offense #1397 (or the newest offense)]

ACTION: Point to the offense card showing:
- Title: "SSH brute force in progress on demo-server from 198.51.100.23"
- Risk: critical
- 16 correlated events, 6 alerts grouped under it
- Timeline: chronological chain of the whole attack
- Related user: svc_deploy
- Attacker IP: 198.51.100.23

TALK TRACK:
- "One Offense, not six alerts and 17 events."
- "The timeline shows the kill chain end to end: brute force → success
  → sudo → root → service impact."
- "Related user svc_deploy, source 198.51.100.23 — the who and the from."
- "One click takes it to the Case Workspace, where it becomes an
  incident with evidence, notes and an audit trail."

KEY MESSAGE: "This is the 'QRadar offense' concept: correlation into a
single narrative with a risk score, not an inbox of alerts."

---------------------------------------------------------------
4. POINT AT MITRE — STOP. TAKE QUESTIONS. (approximately 30 seconds)
---------------------------------------------------------------

ACTION: Point at the MITRE mapping on the offense / the MITRE ATT&CK page.

TALK TRACK:
- **T1110** — Brute Force: the 10 failed logins
- **T1548.003** — Sudo and Sudo Caching: the privilege escalation
- **T1078.003** — Valid Accounts: Local Accounts: the root login

[PAUSE for questions]

KEY MESSAGE: "Every detection maps to a published MITRE technique. The
jury can check these against the public ATT&CK matrix."

---------------------------------------------------------------
5. THE REPLAY DEMONSTRATOR (optional, 30 seconds if asked)
---------------------------------------------------------------

TARGET: "Same chain, again, on demand."

ACTION: In Attack Lab → **History**, press **Replay** on that run.

TALK TRACK: "Replay clears only that run's synthetic artifacts and
re-executes it — you get the same six detections again. Press Reset and
the instance is clean again: every simulated event, alert and timeline
is removed, and real data on the same host is untouched. Purge in the
History tab does it for the whole instance."

KEY MESSAGE: "The demo is repeatable and reversible — important when
the platform already holds real data."

---------------------------------------------------------------
BACKUP PLAN
---------------------------------------------------------------

If the frontend is slow or the stack is not up:

"Let me show the same pipeline through the API." Then run:

  POST /api/v1/simulation/run/multi_stage_attack?host_id=<id>&pace=instant

and read the JSON response back: `event_count`, `alert_count`,
`offense_count` and the `alerts[]` array with titles and MITRE ids.
It is the identical code path the UI calls.

Say clearly: "This is simulated telemetry. The agent parser, detection
rules, correlation engine, offense grouping and MITRE mapping are the
same code that runs for live agent data — only the source of the events
differs, and the UI labels it `[SIMULATED]` so the two can never be
confused."

If a real enrolled Linux host is available (Option B in
docs/DEPLOYMENT.md), run its attack script instead and follow sections
2-4 unchanged — the alert titles will name that host instead of
demo-server.

----------------------------------------------------------------------
END OF SCRIPT
----------------------------------------------------------------------
