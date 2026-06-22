import hashlib
from pathlib import Path

AGENT_DIR = Path("/opt/securi-agent/agent")


def compute_agent_hash() -> str:
    """Hash agent Python sources only — config changes must not trigger false tamper alerts."""
    h = hashlib.sha256()
    if not AGENT_DIR.is_dir():
        return h.hexdigest()
    for p in sorted(AGENT_DIR.glob("**/*.py")):
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()
