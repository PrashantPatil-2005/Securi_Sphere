"""Map OIDC group / role claims to Securi RBAC roles."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

ROLE_PRIORITY = {"admin": 0, "analyst": 1, "viewer": 2}


def parse_oidc_role_map(raw: str) -> dict[str, str]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Invalid OIDC_ROLE_MAP JSON: %s", exc)
        return {}
    if not isinstance(data, dict):
        return {}
    valid_roles = set(ROLE_PRIORITY)
    return {
        str(k): v
        for k, v in data.items()
        if isinstance(v, str) and v in valid_roles
    }


def extract_claim_values(claims: dict[str, Any], claim_name: str) -> list[str]:
    raw = claims.get(claim_name)
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if item is not None]
    return [str(raw)]


def resolve_role_from_claims(claims: dict[str, Any]) -> str:
    """Resolve Securi role from IdP groups/roles claim, else default."""
    role_map = parse_oidc_role_map(settings.oidc_role_map)
    if not role_map:
        return settings.oidc_default_role

    groups = extract_claim_values(claims, settings.oidc_groups_claim)
    matched: list[str] = []
    for group in groups:
        role = role_map.get(group)
        if role:
            matched.append(role)

    if not matched:
        return settings.oidc_default_role

    return min(matched, key=lambda role: ROLE_PRIORITY.get(role, 99))


def email_domain_allowed(email: str) -> bool:
    allowed = (settings.oidc_allowed_email_domains or "").strip()
    if not allowed:
        return True
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1].lower()
    domains = {d.strip().lower() for d in allowed.split(",") if d.strip()}
    return domain in domains
