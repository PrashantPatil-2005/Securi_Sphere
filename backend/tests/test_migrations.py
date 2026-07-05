"""Alembic migration tests."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_single_head():
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["005_agent_cert"]


def test_alembic_revision_chain():
    backend_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    script = ScriptDirectory.from_config(cfg)
    revisions = [rev.revision for rev in script.walk_revisions()]
    assert revisions[0] == "005_agent_cert"
    assert "001_baseline" in revisions
