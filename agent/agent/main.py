import logging
import signal
import socket
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


def _handle_shutdown(signum, frame):
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s — shutting down gracefully", sig_name)
    _shutdown_requested = True


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
            sender.flush_buffer()

            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                sender.heartbeat({"agent_hash": compute_agent_hash(), "agent_version": AGENT_VERSION})
                last_heartbeat = now

            if now - last_metrics >= METRICS_INTERVAL:
                sender.send_metrics([collect_metrics()])
                last_metrics = now

            if now - last_logs >= LOG_INTERVAL:
                events = collect_events(tailer)
                if events:
                    sender.send_events(events)
                last_logs = now

            time.sleep(1)
    finally:
        logger.info("Flushing remaining buffer before exit...")
        sender.flush_buffer()
        logger.info("Agent shutdown complete")


if __name__ == "__main__":
    main()
