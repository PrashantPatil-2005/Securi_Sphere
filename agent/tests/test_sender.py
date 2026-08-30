import requests
from unittest.mock import MagicMock, patch

import pytest

from agent.sender import Sender, MAX_CONSECUTIVE_FAILURES, MAX_RETRIES_BEFORE_BUFFER, _sign


@pytest.fixture()
def sender(tmp_buffer_db):
    import agent.buffer as buf
    buf.init_db()
    s = Sender("https://server.example.com", "test-api-key", signing=False)
    s._interruptible_sleep = lambda seconds: None
    return s


@pytest.fixture()
def mock_session(sender):
    session = MagicMock()
    sender.session = session
    return session


def test_sender_successful_send(sender, mock_session):
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    result = sender.heartbeat()
    assert result is True
    assert sender._consecutive_failures == 0


def test_sender_server_error(sender, mock_session):
    resp = MagicMock()
    resp.status_code = 500
    resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    mock_session.post.return_value = resp
    result = sender.heartbeat()
    assert result is False


def test_sender_network_failure(sender, mock_session):
    mock_session.post.side_effect = requests.ConnectionError("no route")
    result = sender.heartbeat()
    assert result is False


def test_sender_retry_increments_failures(sender, mock_session):
    mock_session.post.side_effect = requests.ConnectionError("down")
    sender.heartbeat()
    sender.heartbeat()
    sender.heartbeat()
    assert sender._consecutive_failures == 3


def test_sender_success_resets_failures(sender, mock_session):
    mock_session.post.side_effect = requests.ConnectionError("down")
    sender.heartbeat()
    sender.heartbeat()
    assert sender._consecutive_failures == 2
    mock_session.post.side_effect = None
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    sender.heartbeat()
    assert sender._consecutive_failures == 0


def test_sender_max_consecutive_failures(sender, mock_session):
    mock_session.post.side_effect = requests.ConnectionError("down")
    for _ in range(MAX_CONSECUTIVE_FAILURES + 50):
        sender.heartbeat()
    assert sender._consecutive_failures == MAX_CONSECUTIVE_FAILURES


def test_sender_buffer_on_failure(sender, mock_session):
    import agent.buffer as buf
    mock_session.post.side_effect = requests.ConnectionError("down")
    for _ in range(MAX_RETRIES_BEFORE_BUFFER):
        sender.send_events([{"type": "test", "n": 1}])
    size_after_buffering = buf.queue_size()
    assert size_after_buffering > 0


def test_sender_flush_buffer(sender, mock_session):
    import agent.buffer as buf
    mock_session.post.side_effect = requests.ConnectionError("down")
    for _ in range(MAX_RETRIES_BEFORE_BUFFER + 1):
        sender.send_events([{"type": "test"}])
    buffered = buf.queue_size()
    assert buffered > 0
    mock_session.post.side_effect = None
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    sender.flush_buffer()
    assert buf.queue_size() == 0


def test_sender_abort_backoff(sender):
    import threading

    def set_abort():
        import time
        time.sleep(0.05)
        sender.abort_backoff()

    t = threading.Thread(target=set_abort)
    t.start()
    sender._consecutive_failures = 1
    sender._interruptible_sleep = Sender._interruptible_sleep.__get__(sender)
    sender._interruptible_sleep(10)
    t.join(timeout=2)
    assert sender._backoff_event.is_set()


def test_sender_hmac_signature(sender, mock_session):
    sender.signing = True
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    sender.heartbeat()
    call_kwargs = mock_session.post.call_args
    headers = call_kwargs.kwargs.get("headers", call_kwargs[1].get("headers", {}))
    assert "X-Agent-Timestamp" in headers
    assert "X-Agent-Nonce" in headers
    assert "X-Agent-Signature" in headers


def test_sender_is_online(sender, mock_session):
    assert sender.is_online is True
    mock_session.post.side_effect = requests.ConnectionError("down")
    sender.heartbeat()
    assert sender.is_online is False
    mock_session.post.side_effect = None
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    sender.heartbeat()
    assert sender.is_online is True
