import json
import os
from pathlib import Path

CONFIG_PATH = Path("/etc/securi/config.json")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text())
    else:
        cfg = {}
    if "signing_enabled" not in cfg:
        env_sign = os.environ.get("SECURI_AGENT_SIGNING", "").lower()
        cfg["signing_enabled"] = env_sign in ("1", "true", "yes")
    return cfg


def save_config(server_url: str, api_key: str, *, signing_enabled: bool = False) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {"server_url": server_url.rstrip("/"), "api_key": api_key, "signing_enabled": signing_enabled},
            indent=2,
        )
    )
    CONFIG_PATH.chmod(0o600)
