import logging
import os
import signal
import sys
import threading
import time

from agent.buffer import init_db, _agent_rss_mb
from agent.collector.logs import collect_events
from agent.collector.events import LogTailer
from agent.collector.metrics import collect_metrics
from agent.config import load_config
from agent.sender import Sender, AGENT_VERSION
from agent.integrity import compute_agent_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("securi-agent")

HEARTBEAT_INTERVAL = 30
METRICS_INTERVAL = 30
LOG_INTERVAL = 10

_shutdown_requested = False
_shutdown_event = threading.Event()


def _handle_shutdown(signum, frame):
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s — shutting down gracefully", sig_name)
    _shutdown_requested = True
    _shutdown_event.set()


def _send_events_with_individual_buffer(sender: Sender, events: list[dict]) -> bool:
    """Send events, buffering individual events on failure instead of batch dicts.

    When the server is unreachable, each event is stored as its own SQLite row
    (~300-2000 bytes per row). This eliminates the batch-wrapper nesting that
    caused the original 'string or blob too big' crash and memory explosion.
    """
    if not events:
        return True
    for start in range(0, len(events), 50):
        chunk = events[start : start + 50]
        success = sender.send_events(chunk)
        if not success:
            from agent.buffer import enqueue_events
            stored = enqueue_events(chunk)
            rss = _agent_rss_mb()
            logger.warning(
                "Server unreachable — buffered %d/%d events individually (rss=%.0fMB)",
                stored, len(chunk), rss,
            )
            return False
    return True


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    init_db()
    config = load_config()
    server_url = config.get("server_url")
    api_key = config.get("api_key")
    if not server_url or not api_key:
        logger.error("Missing config at /etc/securi/config.json")
        raise SystemExit(1)

    sender = Sender(server_url, api_key, signing=bool(config.get("signing_enabled")))
    tailer = LogTailer()
    last_heartbeat = 0.0
    last_metrics = 0.0
    last_logs = 0.0

    rss = _agent_rss_mb()
    logger.info("Securi agent v%s started for %s (rss=%.0fMB)", AGENT_VERSION, server_url, rss)

    try:
        while not _shutdown_requested:
            now = time.time()
            try:
                sender.flush_buffer()
            except Exception:
                logger.exception("Error flushing buffer")

            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                try:
                    sender.heartbeat({"agent_hash": compute_agent_hash(), "agent_version": AGENT_VERSION})
                except Exception:
                    logger.exception("Heartbeat failed")
                last_heartbeat = now

            if now - last_metrics >= METRICS_INTERVAL:
                try:
                    metrics = [collect_metrics()]
                    success = sender.send_metrics(metrics)
                    if not success:
                        from agent.buffer import enqueue_metrics
                        stored = enqueue_metrics(metrics)
                        logger.warning("Server unreachable — buffered %d metrics", stored)
                except Exception:
                    logger.exception("Metrics collection failed")
                last_metrics = now

            if now - last_logs >= LOG_INTERVAL:
                try:
                    events = collect_events(tailer)
                    if events:
                        rss = _agent_rss_mb()
                        event_types = {}
                        for e in events:
                            t = e.get("event_type", "unknown")
                            event_types[t] = event_types.get(t, 0) + 1
                        largest = max((len(e.get("raw_log", "")) for e in events), default=0)
                        logger.info(
                            "Collected %d events (types=%s, largest_raw=%d, rss=%.0fMB)",
                            len(events), event_types, largest, rss,
                        )
                        _send_events_with_individual_buffer(sender, events)
                except Exception:
                    logger.exception("Log collection failed")
                last_logs = now

            _shutdown_event.wait(timeout=1.0)
    finally:
        logger.info("Flushing remaining buffer before exit...")
        try:
            sender.flush_buffer()
        except Exception:
            logger.exception("Final buffer flush failed")
        sender.close()
        logger.info("Agent shutdown complete")


if __name__ == "__main__":
    main()
