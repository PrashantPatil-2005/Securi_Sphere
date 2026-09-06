import logging
import os
import subprocess

from agent.collector.events import LogTailer, parse_line

logger = logging.getLogger(__name__)

MAX_EVENTS_PER_CYCLE = 30
MAX_JOURNAL_OUTPUT_BYTES = 512 * 1024


def collect_events(tailer: LogTailer) -> list[dict]:
    events = []
    for source, line in tailer.read_new_lines():
        source_name = "auth.log" if "auth" in source else "syslog" if "syslog" in source else source
        parsed = parse_line(line, source_name)
        if parsed:
            events.append(parsed)

    if not events:
        for source, line in tailer.read_journald():
            parsed = parse_line(line, "journald")
            if parsed:
                events.append(parsed)

    if len(events) > MAX_EVENTS_PER_CYCLE:
        logger.warning(
            "Event burst capped: %d collected, sending first %d",
            len(events), MAX_EVENTS_PER_CYCLE,
        )
        events = events[:MAX_EVENTS_PER_CYCLE]
    return events
