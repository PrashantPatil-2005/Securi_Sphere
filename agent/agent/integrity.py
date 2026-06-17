import hashlib
from pathlib import Path

AGENT_DIR = Path("/opt/securi-agent/agent")
CONFIG = Path("/etc/securi/config.json")


def compute_agent_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(AGENT_DIR.glob("**/*.py")):
        if p.is_file():
            h.update(p.read_bytes())
    if CONFIG.exists():
        h.update(CONFIG.read_bytes())
    return h.hexdigest()
