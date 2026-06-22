"""Authenticated agent dependency with optional request signing."""
import json

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.database import get_db
from app.models.host import Host
from app.services.agent_auth import validate_agent_request, validate_api_key_host


class AuthenticatedAgent:
    def __init__(self, host: Host, raw_body: bytes):
        self.host = host
        self.raw_body = raw_body

    def parse_json(self) -> dict:
        if not self.raw_body:
            return {}
        return json.loads(self.raw_body)


async def get_authenticated_agent(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> AuthenticatedAgent:
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")
    host = await validate_api_key_host(db, x_api_key)
    raw_body = await request.body()
    await validate_agent_request(db, host, request, raw_body, x_api_key)
    return AuthenticatedAgent(host, raw_body)
