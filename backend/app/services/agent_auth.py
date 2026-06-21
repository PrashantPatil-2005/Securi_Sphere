"""Agent request authentication: replay protection and request signing."""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent_nonce import AgentRequestNonce
from app.models.host import Host
from app.security import hash_token

logger = logging.getLogger(__name__)

MAX_CLOCK_SKEW_SECONDS = 300
NONCE_RETENTION_HOURS = 24


def sign_payload(api_key: str, timestamp: str, nonce: str, body: bytes) -> str:
    message = f"{timestamp}.{nonce}.".encode() + body
    return hmac.new(api_key.encode(), message, hashlib.sha256).hexdigest()


def verify_agent_signature(
    api_key: str,
    timestamp: str,
    nonce: str,
    signature: str,
    body: bytes,
) -> bool:
    expected = sign_payload(api_key, timestamp, nonce, body)
    return hmac.compare_digest(expected, signature)


async def validate_agent_request(
    db: AsyncSession,
    host: Host,
    request: Request,
    raw_body: bytes,
    api_key: str,
) -> None:
    if not settings.agent_request_signing:
        return

    timestamp = request.headers.get("X-Agent-Timestamp")
    nonce = request.headers.get("X-Agent-Nonce")
    signature = request.headers.get("X-Agent-Signature")

    if not all([timestamp, nonce, signature]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing agent security headers")

    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid timestamp format")

    now = datetime.now(timezone.utc)
    skew = abs((now - ts).total_seconds())
    if skew > MAX_CLOCK_SKEW_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Request timestamp out of range")

    if not verify_agent_signature(api_key, timestamp, nonce, signature, raw_body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid request signature")

    existing = (
        await db.execute(
            select(AgentRequestNonce).where(
                AgentRequestNonce.host_id == host.id,
                AgentRequestNonce.nonce == nonce,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Replay detected")

    db.add(AgentRequestNonce(
        host_id=host.id,
        nonce=nonce,
        request_path=request.url.path,
    ))

    cutoff = now - timedelta(hours=NONCE_RETENTION_HOURS)
    await db.execute(delete(AgentRequestNonce).where(AgentRequestNonce.created_at < cutoff))


async def validate_api_key_host(db: AsyncSession, api_key: str) -> Host:
    key_hash = hash_token(api_key)
    host = (
        await db.execute(select(Host).where(Host.api_key_hash == key_hash))
    ).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if host.api_key_revoked_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key revoked")
    return host
