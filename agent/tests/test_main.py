import signal
from unittest.mock import MagicMock, patch

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
    called = {"flag": False}
    original = main_mod._shutdown_requested
    main_mod._shutdown_requested = False
    try:
        frame = MagicMock()
        _handle_shutdown(signal.SIGTERM, frame)
        assert main_mod._shutdown_requested is True
    finally:
        main_mod._shutdown_requested = original
