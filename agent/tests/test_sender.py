import requests
from unittest.mock import MagicMock

import pytest

from agent.sender import Sender, MAX_CONSECUTIVE_FAILURES, MAX_RETRIES_BEFORE_BUFFER


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


def test_sender_401_sets_auth_failed(sender, mock_session):
    resp = MagicMock()
    resp.status_code = 401
    mock_session.post.return_value = resp
    result = sender.heartbeat()
    assert result is False
    assert sender.is_auth_failed is True


def test_sender_401_does_not_buffer(sender, mock_session):
    import agent.buffer as buf
    resp = MagicMock()
    resp.status_code = 401
    mock_session.post.return_value = resp
    for _ in range(MAX_RETRIES_BEFORE_BUFFER + 5):
        sender.send_events([{"type": "test"}])
    assert buf.queue_size() == 0


def test_sender_success_resets_auth_failed(sender, mock_session):
    resp_401 = MagicMock()
    resp_401.status_code = 401
    mock_session.post.return_value = resp_401
    sender.heartbeat()
    assert sender.is_auth_failed is True
    resp_200 = MagicMock()
    resp_200.status_code = 200
    mock_session.post.return_value = resp_200
    sender.heartbeat()
    assert sender.is_auth_failed is False


def test_sender_close(sender, mock_session):
    sender.close()
    mock_session.close.assert_called_once()


def test_sender_flush_batch_size(tmp_buffer_db, sender, mock_session):
    import agent.buffer as buf
    buf.init_db()
    mock_session.post.side_effect = requests.ConnectionError("down")
    for _ in range(MAX_RETRIES_BEFORE_BUFFER + 5):
        sender.send_events([{"n": 1}])
    total_buffered = buf.queue_size()
    assert total_buffered > 0
    mock_session.post.side_effect = None
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    sender.flush_buffer()
    assert buf.queue_size() == 0


def test_sender_flush_batch_chunking(tmp_buffer_db):
    import agent.buffer as buf
    from agent.sender import Sender, MAX_FLUSH_BATCH_SIZE
    buf.init_db()
    s = Sender("https://server.example.com", "test-key", signing=False)
    s._interruptible_sleep = lambda seconds: None
    original = MAX_FLUSH_BATCH_SIZE
    try:
        import agent.sender as sender_mod
        sender_mod.MAX_FLUSH_BATCH_SIZE = 2
        for i in range(6):
            buf.enqueue("events", {"seq": i})
        assert buf.queue_size() == 6
        mock = MagicMock()
        resp = MagicMock()
        resp.status_code = 200
        mock.post.return_value = resp
        s.session = mock
        s.flush_buffer()
        assert buf.queue_size() == 0
        assert mock.post.call_count == 3
    finally:
        sender_mod.MAX_FLUSH_BATCH_SIZE = original


def test_sender_429_respects_retry_after(sender, mock_session):
    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {"Retry-After": "5"}
    mock_session.post.return_value = resp
    sender._interruptible_sleep = lambda s: None
    sender.send_events([{"type": "test"}])
    assert sender._consecutive_failures > 0


def test_sender_logging_throttle(sender, mock_session):
    mock_session.post.side_effect = requests.ConnectionError("down")
    sender._last_failure_log_time = 0.0
    sender.heartbeat()
    sender._failure_log_suppressed = False
    sender.heartbeat()
    assert sender._failure_log_suppressed is True
