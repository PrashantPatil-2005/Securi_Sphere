MIN_STEP_MS = 350
MAX_STEP_MS = 6000


def _replay_step_delay_ms(prev_ts: str, next_ts: str, speed: float) -> int:
    from datetime import datetime

    delta = (datetime.fromisoformat(next_ts.replace("Z", "+00:00")) - datetime.fromisoformat(prev_ts.replace("Z", "+00:00"))).total_seconds() * 1000
    scaled = delta / speed if delta > 0 else 1200 / speed
    return round(min(max(scaled, MIN_STEP_MS), MAX_STEP_MS))


def _replay_progress(current_index: int, total: int) -> int:
    if total <= 1:
        return 100 if total == 1 else 0
    return round((current_index / (total - 1)) * 100)


def test_replay_step_delay_clamps_fast_events():
    delay = _replay_step_delay_ms("2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00.050+00:00", 1)
    assert delay == MIN_STEP_MS


def test_replay_step_delay_scales_with_gap():
    delay = _replay_step_delay_ms("2026-01-01T00:00:00+00:00", "2026-01-01T00:00:10+00:00", 2)
    assert delay == 5000


def test_replay_progress_endpoints():
    assert _replay_progress(0, 5) == 0
    assert _replay_progress(4, 5) == 100
