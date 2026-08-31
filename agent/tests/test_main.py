import signal
from unittest.mock import MagicMock

import pytest

from agent import main as main_mod
from agent.main import _handle_shutdown, main


def test_main_exits_on_missing_config(monkeypatch):
    monkeypatch.setattr("agent.main.init_db", MagicMock())
    monkeypatch.setattr("agent.main.load_config", lambda: {})
    monkeypatch.setattr("agent.main.signal", MagicMock())
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1


def test_main_signal_handler():
    original = main_mod._shutdown_requested
    main_mod._shutdown_requested = False
    try:
        frame = MagicMock()
        _handle_shutdown(signal.SIGTERM, frame)
        assert main_mod._shutdown_requested is True
    finally:
        main_mod._shutdown_requested = original


def test_main_shutdown_event_set_on_signal():
    import threading
    original = main_mod._shutdown_requested
    original_event = main_mod._shutdown_event
    main_mod._shutdown_requested = False
    main_mod._shutdown_event = threading.Event()
    try:
        frame = MagicMock()
        _handle_shutdown(signal.SIGTERM, frame)
        assert main_mod._shutdown_event.is_set()
    finally:
        main_mod._shutdown_requested = original
        main_mod._shutdown_event = original_event


def test_main_collector_exception_does_not_crash(monkeypatch):
    from agent.sender import Sender
    import threading

    mock_sender = MagicMock(spec=Sender)
    mock_sender.flush_buffer = MagicMock()
    mock_sender.heartbeat = MagicMock(side_effect=RuntimeError("collector boom"))
    mock_sender.close = MagicMock()

    monkeypatch.setattr("agent.main.init_db", MagicMock())
    monkeypatch.setattr("agent.main.load_config", lambda: {"server_url": "https://x.com", "api_key": "k"})
    monkeypatch.setattr("agent.main.Sender", lambda *a, **kw: mock_sender)
    monkeypatch.setattr("agent.main.LogTailer", MagicMock())
    monkeypatch.setattr("agent.main.collect_events", MagicMock(side_effect=RuntimeError("collector boom")))
    monkeypatch.setattr("agent.main.collect_metrics", MagicMock(side_effect=RuntimeError("metrics boom")))
    monkeypatch.setattr("agent.main.compute_agent_hash", lambda: "abc")

    call_count = {"n": 0}

    def fake_wait(timeout=None):
        call_count["n"] += 1
        if call_count["n"] >= 3:
            main_mod._shutdown_requested = True
        return True

    shutdown_event = threading.Event()
    monkeypatch.setattr(main_mod, "_shutdown_event", shutdown_event)
    monkeypatch.setattr(shutdown_event, "wait", fake_wait)
    monkeypatch.setattr(main_mod, "_shutdown_requested", False)

    main()
    assert mock_sender.heartbeat.call_count >= 1
    assert mock_sender.close.call_count == 1
