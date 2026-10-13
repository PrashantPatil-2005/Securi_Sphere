import logging
import traceback
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)


def json_safe(value: Any) -> Any:
    """Make validation errors JSON-serializable.

    Pydantic puts the original exception object in ``ctx['error']`` for
    ``value_error`` failures, which ``json.dumps`` cannot encode — the response
    then crashes with a 500 instead of returning the 422 with the real message.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    return str(value)


def error_body(
    *,
    code: str,
    message: str,
    status_code: int,
    details: Any = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "status": status_code,
            "request_id": request_id_var.get(),
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "forbidden" if exc.status_code == 403 else "unauthorized" if exc.status_code == 401 else "http_error"
    if exc.status_code == 429:
        code = "rate_limit_exceeded"
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    headers = dict(exc.headers) if exc.headers else None
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code=code, message=detail, status_code=exc.status_code),
        headers=headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(
            code="validation_error",
            message="Request validation failed",
            status_code=422,
            details=json_safe(exc.errors()),
        ),
    )


async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    logger.warning("Pydantic validation error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=422,
        content=error_body(
            code="validation_error",
            message="Request validation failed",
            status_code=422,
            details=json_safe(exc.errors()),
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s\n%s", request.method, request.url.path, exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=error_body(code="internal_error", message="Internal server error", status_code=500),
    )
