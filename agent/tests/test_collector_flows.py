from unittest.mock import patch

import pytest

from agent.collector.flows import (
    _direction,
    _hex_ip_port,
    collect_flows,
    parse_proc_net_line,
)


def test_hex_ip_port_ipv4():
    # 0100007F:0016 = 127.0.0.1:22
    ip, port = _hex_ip_port("0100007F:0016")
    assert ip == "127.0.0.1"
    assert port == 22


def test_hex_ip_port_invalid():
    ip, port = _hex_ip_port("zzzz")
    assert ip is None
    assert port is None


def test_parse_proc_net_line_skips_header():
    header = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode"
    assert parse_proc_net_line(header, "tcp") is None


def test_parse_proc_net_line_established_tcp():
    # 0: 0100007F:0016 0100007F:C350 01 ... (established loopback)
    line = "   0: 0100007F:0016 0100007F:C350 01 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0"
    sock = parse_proc_net_line(line, "tcp")
    assert sock is not None
    assert sock["local_ip"] == "127.0.0.1"
    assert sock["local_port"] == 22
    assert sock["remote_ip"] == "127.0.0.1"
    assert sock["remote_port"] == 50000
    assert sock["protocol"] == "tcp"


def test_parse_proc_net_line_skips_non_established_tcp():
    # st=0A is LISTEN — not a flow
    line = "   0: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0"
    assert parse_proc_net_line(line, "tcp") is None


def test_parse_proc_net_line_udp_with_remote():
    line = "   0: 00000000:1F90 08080808:0035 07 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0"
    sock = parse_proc_net_line(line, "udp")
    assert sock is not None
    assert sock["protocol"] == "udp"


def test_parse_proc_net_line_udp_listener_skipped():
    # remote port 0 = unconnected listener
    line = "   0: 00000000:0035 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0"
    assert parse_proc_net_line(line, "udp") is None


def test_direction_inbound_vs_outbound():
    listen = {("127.0.0.1", 22)}
    inbound = {"local_ip": "127.0.0.1", "local_port": 22, "remote_ip": "10.0.0.5", "remote_port": 51234, "protocol": "tcp"}
    outbound = {"local_ip": "127.0.0.1", "local_port": 51234, "remote_ip": "10.0.0.5", "remote_port": 22, "protocol": "tcp"}
    assert _direction(inbound, listen) == "inbound"
    assert _direction(outbound, listen) == "outbound"


def test_collect_flows_disabled_on_non_linux():
    with patch("agent.collector.flows.platform.system", return_value="Windows"):
        assert collect_flows(set()) == []


def test_collect_flows_dedupes_against_seen():
    """Second call with the same socket snapshot emits nothing new."""
    proc_content = (
        "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
        "   0: 0100007F:0016 0100007F:C350 01 00000000:00000000 00:00000000 00000000     0        0 12345 1 0000000000000000 100 0 0 10 0\n"
    )

    def fake_open(path, *args, **kwargs):
        if path == "/proc/net/tcp":
            return open_text(proc_content)
        raise OSError(path)

    class open_text:
        def __init__(self, content):
            self._lines = content.splitlines(keepends=True)
        def readlines(self):
            return self._lines
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    with (
        patch("agent.collector.flows.platform.system", return_value="Linux"),
        patch("builtins.open", side_effect=fake_open),
    ):
        seen: set[tuple] = set()
        first = collect_flows(seen)
        second = collect_flows(seen)
    assert len(first) == 1
    assert first[0]["src_ip"] == "127.0.0.1"
    assert first[0]["dst_port"] == 50000
    assert first[0]["protocol"] == "tcp"
    assert first[0]["source"] == "agent-flow-collector"
    assert "timestamp" in first[0]
    assert second == []
