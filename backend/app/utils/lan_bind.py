"""Ensure SERVER_URL's host is a current local IPv4 when it is a LAN address."""

from __future__ import annotations

import ipaddress
import logging
import os
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def running_in_docker() -> bool:
    return Path("/.dockerenv").exists() or os.environ.get("container") == "docker"


def _is_ipv4(host: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(host), ipaddress.IPv4Address)
    except ValueError:
        return False


def local_ipv4_addresses() -> set[str]:
    found: set[str] = {"127.0.0.1"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(info[4][0])
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        found.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    if sys.platform == "win32":
        try:
            raw = subprocess.check_output(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-NetIPAddress -AddressFamily IPv4 | ForEach-Object { $_.IPAddress }",
                ],
                text=True,
                timeout=8,
            )
            for line in raw.splitlines():
                token = line.strip()
                if token and _is_ipv4(token):
                    found.add(token)
        except (OSError, subprocess.SubprocessError):
            logger.debug("could not list Windows IPv4 addresses", exc_info=True)
    return found


def validate_server_url_interface(
    server_url: str,
    *,
    skip: bool = False,
    local_ips: set[str] | None = None,
) -> None:
    """Raise ValueError if SERVER_URL is a LAN IPv4 not assigned on this host."""
    if skip or running_in_docker():
        return
    if not server_url:
        return
    host = urlparse(server_url).hostname or ""
    if not host or host.lower() in _LOOPBACK:
        return
    if not _is_ipv4(host):
        return
    addr = ipaddress.ip_address(host)
    if addr.is_loopback or addr.is_link_local:
        return

    ips = local_ips if local_ips is not None else local_ipv4_addresses()
    lan_ips = sorted(
        ip for ip in ips if _is_ipv4(ip) and not ipaddress.ip_address(ip).is_loopback
    )
    if host in ips:
        return

    listed = ", ".join(lan_ips) if lan_ips else "(none)"
    raise ValueError(
        f"SERVER_URL host {host} is not assigned to any local network interface. "
        f"Current IPv4 addresses: {listed}. "
        "Wi-Fi DHCP leases change — run .\\scripts\\sync-lan-urls.ps1 "
        "(or pass -LanIp <current-ip> to deploy-windows-lan.ps1) and restart the API. "
        "Do not hardcode a LAN IP in source."
    )
