import logging
import signal
import threading
import time

from agent.buffer import init_db
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

    logger.info("Securi agent started for %s", server_url)

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
                    sender.send_metrics([collect_metrics()])
                except Exception:
                    logger.exception("Metrics collection failed")
                last_metrics = now

            if now - last_logs >= LOG_INTERVAL:
                try:
                    events = collect_events(tailer)
                    if events:
                        sender.send_events(events)
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
