"""Linux network flow collector — reads /proc/net sockets and emits FlowIngest-shaped records.

Emits one record per observed socket (TCP/UDP), deduplicated against the previous
snapshot so a steady-state connection is reported once rather than every cycle.
Optional: disabled unless `flow_collector.enabled` is set in config.json; the agent
runs normally without it. On non-Linux hosts or when /proc/net is unavailable the
collector degrades to disabled with a single warning.

Records are metadata-only (addresses, ports, protocol, direction) — no packet
payloads are captured.
"""

import logging
import platform
import socket
import struct
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MAX_FLOWS_PER_CYCLE = 100
PROC_FILES = (
    ("/proc/net/tcp", "tcp"),
    ("/proc/net/tcp6", "tcp"),
    ("/proc/net/udp", "udp"),
    ("/proc/net/udp6", "udp"),
)


def _hex_ip_port(field: str) -> tuple[str | None, int | None]:
    """Parse a /proc/net hex 'IP:PORT' field (little-endian host byte order)."""
    try:
        ip_hex, port_hex = field.split(":")
        port = int(port_hex, 16)
    except (ValueError, AttributeError):
        return None, None
    if len(ip_hex) == 8:  # IPv4
        raw = bytes.fromhex(ip_hex)
        if len(raw) != 4:
            return None, None
        return socket.inet_ntoa(raw[::-1]), port
    if len(ip_hex) == 32:  # IPv6 — four little-endian 32-bit words
        try:
            parts = [ip_hex[i : i + 8] for i in range(0, 32, 8)]
            swapped = b"".join(bytes.fromhex(p)[::-1] for p in parts)
            return socket.inet_ntop(socket.AF_INET6, swapped), port
        except (ValueError, OSError):
            return None, None
    return None, None


def parse_proc_net_line(line: str, protocol: str) -> dict | None:
    """Parse one data line from /proc/net/{tcp,tcp6,udp,udp6}.

    Format: sl local_address rem_address st tx:rx tr:when retrnsmt uid timeout inode
    Only ESTABLISHED (tcp, st=01) and active UDP (st=07/01) entries are kept.
    """
    parts = line.split()
    if len(parts) < 10 or not parts[0].rstrip(":").isdigit():
        return None
    local_ip, local_port = _hex_ip_port(parts[1])
    remote_ip, remote_port = _hex_ip_port(parts[2])
    if local_ip is None or remote_ip is None:
        return None
    state = parts[3]
    if protocol == "tcp" and state != "01":
        return None
    if protocol == "udp" and remote_port == 0:
        return None  # unconnected UDP listener — not a flow
    return {
        "local_ip": local_ip,
        "local_port": local_port,
        "remote_ip": remote_ip,
        "remote_port": remote_port,
        "protocol": protocol,
    }


def _direction(sock: dict, listen_keys: set[tuple[str, int]]) -> str:
    key = (sock["local_ip"], sock["local_port"])
    return "inbound" if key in listen_keys else "outbound"


def collect_flows(seen: set[tuple]) -> list[dict]:
    """Collect flows not present in *seen* (caller-owned dedup set).

    Returns FlowIngest-shaped dicts with UTC timestamp. Appends new keys to
    *seen*; the caller should periodically clear *seen* to bound memory.
    """
    if platform.system() != "Linux":
        return []

    listen_keys: set[tuple[str, int]] = set()
    parsed: list[dict] = []
    try:
        for path, protocol in PROC_FILES:
            try:
                with open(path) as f:
                    lines = f.readlines()
            except OSError:
                continue
            for line in lines[1:]:  # skip header
                sock = parse_proc_net_line(line, protocol)
                if sock is None:
                    continue
                parsed.append(sock)
                if protocol == "tcp" and line.split()[3] == "0A":
                    listen_keys.add((sock["local_ip"], sock["local_port"]))
    except Exception:
        logger.exception("flow collector: failed reading /proc/net — disabling this cycle")
        return []

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    flows: list[dict] = []
    for sock in parsed:
        direction = _direction(sock, listen_keys)
        if direction == "inbound":
            src_ip, src_port = sock["remote_ip"], sock["remote_port"]
            dst_ip, dst_port = sock["local_ip"], sock["local_port"]
        else:
            src_ip, src_port = sock["local_ip"], sock["local_port"]
            dst_ip, dst_port = sock["remote_ip"], sock["remote_port"]
        key = (src_ip, dst_ip, src_port, dst_port, sock["protocol"])
        if key in seen:
            continue
        seen.add(key)
        flows.append(
            {
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "protocol": sock["protocol"],
                "direction": direction,
                "severity": "info",
                "source": "agent-flow-collector",
                "timestamp": now,
            }
        )
        if len(flows) >= MAX_FLOWS_PER_CYCLE:
            logger.warning("flow collector: capped at %d flows this cycle", MAX_FLOWS_PER_CYCLE)
            break
    return flows
