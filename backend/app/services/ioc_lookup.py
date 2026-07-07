"""IOC enrichment via VirusTotal (optional)."""

from __future__ import annotations

import logging
import re

import httpx

from app.config import settings
from app.core.circuit_breaker import CircuitOpenError
from app.core.circuit_guard import run_async
from app.core.http_timeouts import outbound_timeout

logger = logging.getLogger(__name__)

IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
HASH_RE = re.compile(r"^[a-fA-F0-9]{32,64}$")


def classify_ioc(value: str) -> str | None:
    value = value.strip()
    if IP_RE.match(value):
        return "ip"
    if HASH_RE.match(value):
        return "file" if len(value) == 32 or len(value) == 40 else "file"
    if "." in value and not value.startswith("/"):
        return "domain"
    return None


async def lookup_virustotal(ioc: str) -> dict:
    if not settings.virustotal_api_key:
        return {"ioc": ioc, "backend": "none", "message": "VIRUSTOTAL_API_KEY not configured"}

    kind = classify_ioc(ioc)
    if not kind:
        return {"ioc": ioc, "backend": "virustotal", "error": "Unsupported IOC format"}

    path = {"ip": f"ip_addresses/{ioc}", "domain": f"domains/{ioc}", "file": f"files/{ioc}"}[kind]
    url = f"https://www.virustotal.com/api/v3/{path}"
    headers = {"x-apikey": settings.virustotal_api_key}

    try:
        async def _fetch():
            async with httpx.AsyncClient(timeout=outbound_timeout(short=True)) as client:
                return await client.get(url, headers=headers)

        res = await run_async("virustotal", _fetch)
        if res.status_code == 404:
            return {"ioc": ioc, "kind": kind, "backend": "virustotal", "found": False}
        res.raise_for_status()
        data = res.json().get("data", {})
        attrs = data.get("attributes", {})
        stats = attrs.get("last_analysis_stats", {})
        return {
            "ioc": ioc,
            "kind": kind,
            "backend": "virustotal",
            "found": True,
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0),
            "harmless": stats.get("harmless", 0),
            "undetected": stats.get("undetected", 0),
            "reputation": attrs.get("reputation"),
            "link": f"https://www.virustotal.com/gui/{kind}/{ioc}",
        }
    except CircuitOpenError:
        return {"ioc": ioc, "kind": kind, "backend": "virustotal", "error": "circuit_open"}
    except Exception as exc:
        logger.warning("VirusTotal lookup failed: %s", exc)
        return {"ioc": ioc, "kind": kind, "backend": "virustotal", "error": str(exc)}
