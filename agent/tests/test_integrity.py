from pathlib import Path

from agent.integrity import compute_agent_hash


def test_compute_hash_deterministic(tmp_agent_dir: Path) -> None:
    (tmp_agent_dir / "main.py").write_text("print('hello')")
    h1 = compute_agent_hash()
    h2 = compute_agent_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_compute_hash_differs_on_content(tmp_agent_dir: Path) -> None:
    (tmp_agent_dir / "a.py").write_text("x = 1")
    h1 = compute_agent_hash()
    (tmp_agent_dir / "a.py").write_text("x = 2")
    h2 = compute_agent_hash()
    assert h1 != h2


def test_compute_hash_missing_dir(tmp_path: Path, monkeypatch) -> None:
    missing = tmp_path / "nope"
    monkeypatch.setattr("agent.integrity.AGENT_DIR", missing)
    h = compute_agent_hash()
    assert len(h) == 64
    assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_compute_hash_no_py_files(tmp_agent_dir: Path) -> None:
    (tmp_agent_dir / "notes.txt").write_text("not python")
    h = compute_agent_hash()
    assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_compute_hash_ignores_non_py(tmp_agent_dir: Path) -> None:
    (tmp_agent_dir / "data.txt").write_text("ignore me")
    h_no_py = compute_agent_hash()
    (tmp_agent_dir / "a.py").write_text("x = 1")
    h_with_py = compute_agent_hash()
    assert h_no_py != h_with_py
