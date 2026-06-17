from agent.collector.events import LogTailer, parse_line


def collect_events(tailer: LogTailer) -> list[dict]:
    events = []
    for source, line in tailer.read_new_lines():
        source_name = "auth.log" if "auth" in source else "syslog" if "syslog" in source else source
        parsed = parse_line(line, source_name)
        if parsed:
            events.append(parsed)
    for source, line in tailer.read_journald():
        parsed = parse_line(line, "journald")
        if parsed:
            events.append(parsed)
    return events
