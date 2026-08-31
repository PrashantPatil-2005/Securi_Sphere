from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.collector.events import LogTailer, parse_line


def test_parse_line_ssh_success():
    result = parse_line("Accepted password for root from 10.0.0.1", "auth.log")
    assert result is not None
    assert result["event_type"] == "root_login"
    assert result["severity"] == "high"
    assert "root" in result["description"]


def test_parse_line_ssh_success_non_root():
    result = parse_line("Accepted password for admin from 10.0.0.1", "auth.log")
    assert result is not None
    assert result["event_type"] == "ssh_login_success"
    assert result["severity"] == "low"


def test_parse_line_ssh_failure():
    result = parse_line("Failed password for root from 10.0.0.1", "auth.log")
    assert result is not None
    assert result["event_type"] == "ssh_login_failure"
    assert result["severity"] == "medium"


def test_parse_line_ssh_invalid():
    result = parse_line("Invalid user admin from 10.0.0.1", "auth.log")
    assert result is not None
    assert result["event_type"] == "ssh_login_failure"
    assert result["severity"] == "medium"


def test_parse_line_sudo():
    result = parse_line("sudo: admin :", "auth.log")
    assert result is not None
    assert result["event_type"] == "sudo_usage"
    assert result["severity"] == "low"
    assert "admin" in result["description"]


def test_parse_line_root_login():
    result = parse_line("session opened for user root", "auth.log")
    assert result is not None
    assert result["event_type"] == "root_login"
    assert result["severity"] == "high"


def test_parse_line_service_start():
    result = parse_line("Started nginx.", "syslog")
    assert result is not None
    assert result["event_type"] == "service_start"
    assert "nginx" in result["description"]


def test_parse_line_service_stop():
    result = parse_line("Stopped nginx.", "syslog")
    assert result is not None
    assert result["event_type"] == "service_stop"
    assert "nginx" in result["description"]


def test_parse_line_service_fail():
    result = parse_line("Failed to start nginx", "syslog")
    assert result is not None
    assert result["event_type"] == "service_failure"
    assert result["severity"] == "high"
    assert "nginx" in result["description"]


def test_parse_line_empty():
    assert parse_line("", "auth.log") is None


def test_parse_line_unrecognized():
    assert parse_line("random garbage line with no patterns", "auth.log") is None


def test_log_tailer_read_new_lines(tmp_log_dir: Path, monkeypatch):
    monkeypatch.setattr(
        "agent.collector.events.LOG_PATHS",
        [str(tmp_log_dir / "auth.log"), str(tmp_log_dir / "syslog")],
    )
    auth = tmp_log_dir / "auth.log"
    auth.write_text("Accepted password for root from 10.0.0.1\n")
    tailer = LogTailer()
    lines = tailer.read_new_lines()
    assert len(lines) == 1
    assert "root" in lines[0][1]


def test_log_tailer_position_tracking(tmp_log_dir: Path, monkeypatch):
    monkeypatch.setattr(
        "agent.collector.events.LOG_PATHS",
        [str(tmp_log_dir / "auth.log")],
    )
    auth = tmp_log_dir / "auth.log"
    auth.write_text("line1\nline2\n")
    tailer = LogTailer()
    lines1 = tailer.read_new_lines()
    assert len(lines1) == 2
    auth.write_text("line1\nline2\nline3\n")
    lines2 = tailer.read_new_lines()
    assert len(lines2) == 1
    assert "line3" in lines2[0][1]


def test_log_tailer_journald_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("agent.collector.events.LOG_PATHS", [str(tmp_path / "nonexistent.log")])
    mock_output = MagicMock()
    mock_output.stdout = "journald line 1\njournald line 2\n"
    with patch("agent.collector.events.subprocess.run", return_value=mock_output) as mock_run:
        tailer = LogTailer()
        lines = tailer.read_journald()
        mock_run.assert_called_once()
        assert len(lines) == 2
        assert lines[0][0] == "journald"


def test_log_tailer_journald_skipped_when_files_exist(tmp_log_dir: Path, monkeypatch):
    monkeypatch.setattr(
        "agent.collector.events.LOG_PATHS",
        [str(tmp_log_dir / "auth.log")],
    )
    tailer = LogTailer()
    lines = tailer.read_journald()
    assert lines == []
