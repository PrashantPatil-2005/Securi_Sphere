import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_PATHS = ["/var/log/auth.log", "/var/log/syslog"]

# SSH patterns — ordered by specificity to catch real sshd auth.log lines
SSH_SUCCESS_RE = re.compile(
    r"Accepted (?:publickey|password|keyboard-interactive|gssapi-with-mic|"
    r"hostbased) for (\S+) from ([\d.]+) port \d+ ssh2", re.I
)
SSH_FAILURE_RE = re.compile(
    r"Failed (?:password|publickey|keyboard-interactive|gssapi-with-mic|"
    r"hostbased|preauth) for (\S+) from ([\d.]+) port \d+ ssh2", re.I
)
SSH_INVALID_RE = re.compile(r"Invalid user (\S+) from ([\d.]+)", re.I)
# Also catch "Failed passwords" (plural) and "pam_unix" auth failures
SSH_ANY_FAILURE_RE = re.compile(r"Failed\s+password", re.I)
# Disconnected messages
SSH_DISCONNECT_RE = re.compile(r"Disconnected from (\S+) port \d+ ", re.I)
# Root login alt pattern
ROOT_LOGIN_RE = re.compile(r"session opened for user root", re.I)
# Sudo patterns — try "session opened for <user>" first, then "sudo: <user> :"
SUDO_SESSION_RE = re.compile(r"session opened for (\S+)", re.I)
SUDO_COLON_RE = re.compile(r"sudo:\s+(\S+)\s+:", re.I)
# Service patterns
SERVICE_START_RE = re.compile(r"Started (.+)", re.I)
SERVICE_STOP_RE = re.compile(r"Stopped (.+)", re.I)
SERVICE_FAIL_RE = re.compile(r"Failed to start (.+)", re.I)

MAX_RAW_LOG_LEN = 2048


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truncate(raw: str) -> str:
    if len(raw) <= MAX_RAW_LOG_LEN:
        return raw
    return raw[:MAX_RAW_LOG_LEN]


def _extract_user_and_ip_from_failure(line: str):
    """Try to extract username and IP from various failed login patterns."""
    # Pattern: "Failed password for invalid user user from IP port port ssh2"
    m = re.search(r"Failed\s+password\s+(?:invalid\s+user\s+)?(\S+)\s+from\s+(\S+)", line, re.I)
    if m:
        return m.group(1), m.group(2)
    # Pattern: "Failed password for user from IP port port ssh2"
    m = re.search(r"Failed\s+password\s+for\s+(\S+)\s+from\s+(\S+)", line, re.I)
    if m:
        return m.group(1), m.group(2)
    # Pattern: "Failed publickey for user from IP port port ssh2"
    m = re.search(r"Failed\s+(?:publickey|password|keyboard-interactive|gssapi)\s+for\s+(\S+)\s+from\s+(\S+)", line, re.I)
    if m:
        return m.group(1), m.group(2)
    return None, None


def parse_line(line: str, source: str) -> dict | None:
    line = line.strip()
    if not line or len(line) > 50000:
        return None
    raw = _truncate(line)

    m = SSH_SUCCESS_RE.search(line)
    if m:
        # Groups: 1=username, 2=IP (the (?:...) is non-capturing)
        username = m.group(1)
        ip = m.group(2)
        sev = "high" if username == "root" else "low"
        etype = "root_login" if username == "root" else "ssh_login_success"
        desc = f"SSH login success for {username}"
        return {"event_type": etype, "severity": sev, "description": desc, "source": source, "raw_log": raw,
                "timestamp": _now_iso(), "source_ip": ip, "username": username}

    m = SSH_FAILURE_RE.search(line)
    if m:
        # Groups: 1=username, 2=IP (the (?:...) is non-capturing)
        user = m.group(1)
        ip = m.group(2)
        return {
            "event_type": "ssh_login_failure",
            "severity": "medium",
            "description": "SSH login failure",
            "source": source,
            "raw_log": raw,
            "timestamp": _now_iso(),
            "source_ip": ip,
            "username": user,
        }

    m = SSH_INVALID_RE.search(line)
    if m:
        user = m.group(1)
        ip = m.group(2)
        return {
            "event_type": "ssh_login_failure",
            "severity": "medium",
            "description": f"Invalid user {user} from {ip}",
            "source": source,
            "raw_log": raw,
            "timestamp": _now_iso(),
            "source_ip": ip,
            "username": user,
        }

    # Fallback: try to extract user+IP from any "Failed password" line
    if SSH_ANY_FAILURE_RE.search(line):
        user, ip = _extract_user_and_ip_from_failure(line)
        if user and ip:
            return {
                "event_type": "ssh_login_failure",
                "severity": "medium",
                "description": f"SSH login failure for {user}",
                "source": source,
                "raw_log": raw,
                "timestamp": _now_iso(),
                "source_ip": ip,
                "username": user,
            }

    if ROOT_LOGIN_RE.search(line):
        return {"event_type": "root_login", "severity": "high", "description": "Root login attempt", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SUDO_SESSION_RE.search(line)
    if m:
        return {"event_type": "sudo_usage", "severity": "low", "description": f"Sudo used by {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SUDO_COLON_RE.search(line)
    if m:
        return {"event_type": "sudo_usage", "severity": "low", "description": f"Sudo used by {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SERVICE_FAIL_RE.search(line)
    if m:
        return {"event_type": "service_failure", "severity": "high", "description": f"Service failed: {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SERVICE_START_RE.search(line)
    if m:
        return {"event_type": "service_start", "severity": "info", "description": f"Service started: {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SERVICE_STOP_RE.search(line)
    if m:
        return {"event_type": "service_stop", "severity": "info", "description": f"Service stopped: {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    return None


class LogTailer:
    def __init__(self) -> None:
        self.positions: dict[str, int] = {}

    def _file_logs_available(self) -> bool:
        return any(Path(p).exists() for p in LOG_PATHS)

    def read_new_lines(self) -> list[tuple[str, str]]:
        lines: list[tuple[str, str]] = []
        for path in LOG_PATHS:
            p = Path(path)
            if not p.exists():
                continue
            pos = self.positions.get(path, 0)
            with p.open("r", errors="ignore") as f:
                f.seek(pos)
                new = f.readlines()
                self.positions[path] = f.tell()
            for line in new:
                lines.append((path, line))
        return lines

    def read_journald(self) -> list[tuple[str, str]]:
        # Avoid duplicate events when classic log files are present.
        if self._file_logs_available():
            return []
        try:
            out = subprocess.run(
                ["journalctl", "--since", "15 seconds ago", "--no-pager", "-q"],
                capture_output=True, text=True, timeout=10,
            )
            output = out.stdout
            if len(output) > 512 * 1024:
                logger.warning(
                    "Journald output truncated: %d bytes -> 512KB",
                    len(output),
                )
                output = output[:512 * 1024]
            return [("journald", line) for line in output.splitlines() if line.strip()]
        except (FileNotFoundError, subprocess.SubprocessError):
            return []
