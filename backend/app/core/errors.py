from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var


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
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code=code, message=detail, status_code=exc.status_code),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body(
            code="validation_error",
            message="Request validation failed",
            status_code=422,
            details=exc.errors(),
        ),
    )
