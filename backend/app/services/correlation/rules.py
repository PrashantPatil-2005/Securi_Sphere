"""Built-in correlation rule definitions."""

DEFAULT_CORRELATION_RULES = [
    {
        "name": "Brute Force Success",
        "description": "Multiple failed logins followed by successful login — credential compromise indicator",
        "event_sequence": ["ssh_login_failure", "ssh_login_success"],
        "window_minutes": 15,
        "min_occurrences": {"ssh_login_failure": 3},
        "severity": "critical",
        "confidence_base": 0.80,
        "is_system": True,
    },
    {
        "name": "Privilege Escalation Suspicion",
        "description": "Failed login followed by sudo usage — possible unauthorized privilege escalation",
        "event_sequence": ["ssh_login_failure", "sudo_usage"],
        "window_minutes": 20,
        "min_occurrences": {"ssh_login_failure": 2},
        "severity": "high",
        "confidence_base": 0.70,
        "is_system": True,
    },
    {
        "name": "Brute Force to Privilege Escalation",
        "description": "Failed logins followed by success and sudo usage",
        "event_sequence": ["ssh_login_failure", "ssh_login_success", "sudo_usage"],
        "window_minutes": 20,
        "min_occurrences": {"ssh_login_failure": 3},
        "severity": "critical",
        "confidence_base": 0.85,
        "is_system": True,
    },
    {
        "name": "Potential Host Compromise",
        "description": "Service stop combined with agent disconnect — possible host takeover",
        "event_sequence": ["service_stop", "agent_disconnect"],
        "window_minutes": 30,
        "min_occurrences": {},
        "severity": "critical",
        "confidence_base": 0.75,
        "is_system": True,
    },
    {
        "name": "Service Failure Chain",
        "description": "Multiple service failures indicating systemic degradation",
        "event_sequence": ["service_failure"],
        "window_minutes": 10,
        "min_occurrences": {"service_failure": 3},
        "severity": "high",
        "confidence_base": 0.60,
        "is_system": True,
    },
]

# Rules using co-occurrence matcher (stored with special prefix in description or via future rule_type column)
CO_OCCURRENCE_RULES = [
    {
        "name": "Potential Host Compromise (Co-Occurrence)",
        "description": "[co_occurrence] Service stop with agent disconnect",
        "event_sequence": ["service_stop", "agent_disconnect"],
        "window_minutes": 30,
        "min_occurrences": {},
        "severity": "critical",
        "confidence_base": 0.78,
        "is_system": True,
    },
]
