"""Abort slow HTTP requests before they exhaust worker capacity."""

from __future__ import annotations

import asyncio
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.core.errors import error_body
from app.core.http_timeouts import resolve_request_timeout
from app.core.logging import request_id_var

logger = logging.getLogger(__name__)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.request_timeout_enabled or request.scope.get("type") == "websocket":
            return await call_next(request)

        timeout = resolve_request_timeout(request.url.path)
        if timeout is None:
            return await call_next(request)

        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "request timed out",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "timeout_seconds": timeout,
                },
            )
            return JSONResponse(
                status_code=504,
                content=error_body(
                    code="request_timeout",
                    message="Request timed out",
                    status_code=504,
                    details={"timeout_seconds": timeout},
                ),
                headers={"X-Request-ID": request_id_var.get() or ""},
            )
