import sys
from pathlib import Path

import pytest

AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))


@pytest.fixture()
def tmp_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cfg = tmp_path / "config.json"
    monkeypatch.setattr("agent.config.CONFIG_PATH", cfg)
    return cfg


@pytest.fixture()
def tmp_buffer_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db = tmp_path / "buffer.db"
    monkeypatch.setattr("agent.buffer.DB_PATH", db)
    return db


@pytest.fixture()
def tmp_agent_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "agent_src"
    d.mkdir()
    monkeypatch.setattr("agent.integrity.AGENT_DIR", d)
    return d


@pytest.fixture()
def tmp_log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "logs"
    d.mkdir()
    auth_log = d / "auth.log"
    syslog = d / "syslog"
    auth_log.touch()
    syslog.touch()
    log_paths = [str(auth_log), str(syslog)]
    monkeypatch.setattr("agent.collector.events.LOG_PATHS", log_paths)
    return d
