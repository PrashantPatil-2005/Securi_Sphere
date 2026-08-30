import json
import os
import sys
import stat
from pathlib import Path

import pytest

from agent.config import load_config, save_config


def test_load_config_missing_file(tmp_config_path: Path) -> None:
    if tmp_config_path.exists():
        tmp_config_path.unlink()
    cfg = load_config()
    assert isinstance(cfg, dict)
    assert cfg["signing_enabled"] is False


def test_load_config_valid_json(tmp_config_path: Path) -> None:
    tmp_config_path.write_text(json.dumps({"server_url": "https://s.example.com", "api_key": "k1"}))
    cfg = load_config()
    assert cfg["server_url"] == "https://s.example.com"
    assert cfg["api_key"] == "k1"


def test_load_config_signing_from_env(tmp_config_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if tmp_config_path.exists():
        tmp_config_path.unlink()
    monkeypatch.setenv("SECURI_AGENT_SIGNING", "1")
    cfg = load_config()
    assert cfg["signing_enabled"] is True


def test_save_config_creates_file(tmp_config_path: Path) -> None:
    if tmp_config_path.exists():
        tmp_config_path.unlink()
    save_config("https://s.example.com", "apikey123", signing_enabled=True)
    assert tmp_config_path.exists()
    mode = tmp_config_path.stat().st_mode & 0o777
    if sys.platform != "win32":
        assert mode == 0o600
    data = json.loads(tmp_config_path.read_text())
    assert data["server_url"] == "https://s.example.com"
    assert data["api_key"] == "apikey123"
    assert data["signing_enabled"] is True


def test_save_config_roundtrip(tmp_config_path: Path) -> None:
    if tmp_config_path.exists():
        tmp_config_path.unlink()
    save_config("https://api.test.io", "key_abc", signing_enabled=False)
    cfg = load_config()
    assert cfg["server_url"] == "https://api.test.io"
    assert cfg["api_key"] == "key_abc"
    assert cfg["signing_enabled"] is False
