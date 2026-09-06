import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LOG_PATHS = ["/var/log/auth.log", "/var/log/syslog"]
SSH_SUCCESS = re.compile(r"Accepted (\w+) for (\w+) from ([\d.]+)", re.I)
SSH_FAILURE = re.compile(r"Failed (\w+) for (\w+) from ([\d.]+)", re.I)
SSH_INVALID = re.compile(r"Invalid user (\w+) from ([\d.]+)", re.I)
SUDO = re.compile(r"sudo:\s+(\w+) :", re.I)
ROOT_LOGIN = re.compile(r"session opened for user root", re.I)
SERVICE_START = re.compile(r"Started (.+)\.", re.I)
SERVICE_STOP = re.compile(r"Stopped (.+)\.", re.I)
SERVICE_FAIL = re.compile(r"Failed to start (.+)", re.I)

MAX_RAW_LOG_LEN = 2048


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truncate(raw: str) -> str:
    if len(raw) <= MAX_RAW_LOG_LEN:
        return raw
    return raw[:MAX_RAW_LOG_LEN]


def parse_line(line: str, source: str) -> dict | None:
    line = line.strip()
    if not line or len(line) > 50000:
        return None
    raw = _truncate(line)

    m = SSH_SUCCESS.search(line)
    if m:
        user = m.group(2)
        sev = "high" if user == "root" else "low"
        etype = "root_login" if user == "root" else "ssh_login_success"
        return {"event_type": etype, "severity": sev, "description": f"SSH login success for {user}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SSH_FAILURE.search(line) or SSH_INVALID.search(line)
    if m:
        return {"event_type": "ssh_login_failure", "severity": "medium", "description": "SSH login failure", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    if ROOT_LOGIN.search(line):
        return {"event_type": "root_login", "severity": "high", "description": "Root login attempt", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SUDO.search(line)
    if m:
        return {"event_type": "sudo_usage", "severity": "low", "description": f"Sudo used by {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SERVICE_FAIL.search(line)
    if m:
        return {"event_type": "service_failure", "severity": "high", "description": f"Service failed: {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SERVICE_START.search(line)
    if m:
        return {"event_type": "service_start", "severity": "info", "description": f"Service started: {m.group(1)}", "source": source, "raw_log": raw, "timestamp": _now_iso()}

    m = SERVICE_STOP.search(line)
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
