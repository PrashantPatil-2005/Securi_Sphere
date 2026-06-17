import logging
import socket
import time

from agent.buffer import init_db
from agent.collector.logs import collect_events
from agent.collector.events import LogTailer
from agent.collector.metrics import collect_metrics
from agent.config import load_config
from agent.sender import Sender
from agent.integrity import compute_agent_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("securi-agent")

HEARTBEAT_INTERVAL = 30
METRICS_INTERVAL = 30
LOG_INTERVAL = 10


def main() -> None:
    init_db()
    config = load_config()
    server_url = config.get("server_url")
    api_key = config.get("api_key")
    if not server_url or not api_key:
        logger.error("Missing config at /etc/securi/config.json")
        raise SystemExit(1)

    sender = Sender(server_url, api_key)
    tailer = LogTailer()
    last_heartbeat = 0.0
    last_metrics = 0.0
    last_logs = 0.0

    logger.info("Securi agent started for %s", server_url)

    while True:
        now = time.time()
        sender.flush_buffer()

        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            sender.heartbeat({"agent_hash": compute_agent_hash(), "agent_version": "1.1.0"})
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


if __name__ == "__main__":
    main()
