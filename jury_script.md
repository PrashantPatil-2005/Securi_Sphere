JURY SCRIPT — 5-Minute Attack Scenario Script
================================================

VIVA VOCE SCRIPT FOR SECURI DEMONSTRATION

[ ] Show host online + agent token working
[ ] Start the Linux attack script; show raw log for 10 seconds ("this is the evidence")
[ ] Switch to Alerts: "The SIEM named it."
[ ] Switch to Offense timeline: "It correlated the kill chain."
[ ] Point at MITRE. Stop. Take questions.

----------------------------------------------------------------------

SCRIPT (approximately 5 minutes)

---------------------------------------------------------------
1. HOST STATUS (approximately 30 seconds)
---------------------------------------------------------------

TARGET: "This is our Linux host, currently online and enrolled in Securi.
The agent is actively sending telemetry — you can see the heartbeat
is green, the token is valid, and the host is registered."

ACTION: Point to the dashboard showing host status = "online".
KEY POINT: The agent is running, classifying events in real-time.

---------------------------------------------------------------
2. RAW EVIDENCE — 10 SECONDS (approximately 1 minute)
---------------------------------------------------------------

TARGET: "Here is the raw authentication log from the host. This is
the raw evidence — the uninterpreted auth.log file."

[SHOW raw auth.log output for ~10 seconds, scrolling or fixed window]

[POINT at the screen] "These are the raw log lines — 12 failed SSH
attempts, followed by one success, followed by sudo usage."

TALK TRACK: "This is what the Linux box generates — pure log data. The
jury needs to see that this becomes classified events, then alerts, then
one offense story."

---------------------------------------------------------------
3. SWITCH TO ALERTS — "THE SIEM NAMED IT" (approximately 1 minute)
---------------------------------------------------------------

TARGET: "Now let me switch to the SIEM alerts. The raw logs alone are
just noise — but the SIEM has classified them and named the attack."

[CLICK to Alerts view]

ACTION: Point to the alert list showing:
- "SSH brute force in progress on [hostname] from [source IP]"
- "Privilege escalation detected on [hostname]"
- "Compromised account — SSH success after failures"

TALK TRACK:
- "12 failed logins in 5 minutes → alert named 'Brute Force Attempt'"
- "MITRE T1110 — Credential Access, Brute Force"
- "One successful login after failures → alert named 'Compromised Account'"
- "MITRE T1110 + T1078 — Credential Access + Initial Access"
- "Sudo usage → alert named 'Privilege Escalation Detected'"
- "MITRE T1548.003 — Privilege Escalation"

KEY MESSAGE: "The SIEM named this attack. It didn't just show logs — it
said 'this is a brute force attack,' 'this is privilege escalation,' and
'this account is compromised.' That's what the jury needs to hear."

---------------------------------------------------------------
4. SWITCH TO OFFENSE TIMELINE — "IT CORRELATED THE KILL CHAIN" (approximately 1 minute)
---------------------------------------------------------------

TARGET: "Now let me show the offense — the SIEM's correlation of the
entire kill chain into one story, not 50 separate lines."

[CLICK to Offense view]

ACTION: Point to the offense card showing:
- Title: "Likely SSH account compromise"
- Timeline: chronological chain of events
- Related user: admin
- Attacker IP: 192.168.x.x
- Event count: 14 events
- Alert count: 3 alerts

TALK TRACK:
- "This is one Offense, not 40."
- "The timeline shows the kill chain: brute force → success → sudo"
- "Related user: admin — the account that was compromised"
- "Attacker IP: 192.168.x.x — the source of the attacks"
- "One click takes you to the Case Workspace / Incident"

KEY MESSAGE: "The offense groups everything. You can see the full
story in one place: what happened, when, on which host, and why it's
an attack. This is the 'QRadar offense' the jury asks about."

---------------------------------------------------------------
5. POINT AT MITRE — STOP. TAKE QUESTIONS. (approximately 30 seconds)
---------------------------------------------------------------

TARGET: "Look at the MITRE techniques on the offense card."

[POINT at MITRE mapping on the screen]

TALK TRACK:
- "T1110 — Brute Force: Password Guessing (the 12 failed logins)"
- "T1078 — Valid Accounts: the successful login after failures"
- "T1548.003 — Sudo and Sudo Caching (the privilege escalation)"
- "T1078.003 — Valid Accounts: Local Accounts (if root login was involved)"

[PAUSE for questions]

KEY MESSAGE: "All three tactics map to MITRE. The jury can see the full
attack chain mapped to recognized techniques. This isn't made-up — these
are the same MITRE techniques used globally to describe SSH compromise."

---------------------------------------------------------------
BACKUP PLAN (if live SSH is flaky):
---------------------------------------------------------------

"If the live SSH connection is flaky, I'll run the Attack Lab
multi-stage attack instead and say clearly: 'This is the same pipeline,
simulated telemetry — the agent parser, detection rules, correlation
engine, and offense timeline are all identical. The only difference is
the source of the events — live logs vs. simulated steps. The jury sees
the same named alerts, the same correlated offense, and the same MITRE
labels.'"

----------------------------------------------------------------------
END OF SCRIPT
----------------------------------------------------------------------