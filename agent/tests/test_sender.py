import requests
from unittest.mock import MagicMock

import pytest

from agent.sender import Sender, MAX_CONSECUTIVE_FAILURES


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


def test_sender_send_events_returns_false_on_failure(sender, mock_session):
    mock_session.post.side_effect = requests.ConnectionError("down")
    result = sender.send_events([{"type": "test", "n": 1}])
    assert result is False


def test_sender_flush_buffer(tmp_buffer_db, sender, mock_session):
    import agent.buffer as buf
    for i in range(5):
        buf.enqueue_event({"type": "test", "n": i})
    buffered = buf.queue_size()
    assert buffered == 5
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
    for i in range(10):
        buf.enqueue_event({"n": i})
    total_buffered = buf.queue_size()
    assert total_buffered == 10
    mock_session.post.side_effect = None
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    sender.flush_buffer()
    assert buf.queue_size() == 0


def test_sender_flush_batch_chunking(tmp_buffer_db):
    import agent.buffer as buf
    from agent.sender import Sender
    import agent.sender as sender_mod
    buf.init_db()
    s = Sender("https://server.example.com", "test-key", signing=False)
    s._interruptible_sleep = lambda seconds: None
    original = sender_mod.MAX_FLUSH_BATCH_SIZE
    try:
        sender_mod.MAX_FLUSH_BATCH_SIZE = 2
        for i in range(6):
            buf.enqueue_event({"seq": i})
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


def test_flush_sends_buffered_metrics_to_metrics_endpoint(tmp_buffer_db, sender, mock_session):
    import agent.buffer as buf
    buf.enqueue_metrics([{"cpu_percent": 3.0, "recorded_at": "2026-09-06T00:00:00Z"}])
    buf.enqueue_event({
        "event_type": "ssh_login_failure",
        "severity": "medium",
        "timestamp": "2026-09-06T00:00:00Z",
    })
    resp = MagicMock()
    resp.status_code = 200
    mock_session.post.return_value = resp
    sender.flush_buffer()
    assert buf.queue_size() == 0
    paths = [call.args[0] for call in mock_session.post.call_args_list]
    assert any(p.endswith("/api/v1/agent/events") for p in paths)
    assert any(p.endswith("/api/v1/agent/metrics") for p in paths)


def test_sender_logging_throttle(sender, mock_session):
    mock_session.post.side_effect = requests.ConnectionError("down")
    sender._last_failure_log_time = 0.0
    sender.heartbeat()
    sender._failure_log_suppressed = False
    sender.heartbeat()
    assert sender._failure_log_suppressed is True
