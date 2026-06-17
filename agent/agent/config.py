import json
from pathlib import Path

CONFIG_PATH = Path("/etc/securi/config.json")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(server_url: str, api_key: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"server_url": server_url.rstrip("/"), "api_key": api_key}, indent=2))
    CONFIG_PATH.chmod(0o600)
