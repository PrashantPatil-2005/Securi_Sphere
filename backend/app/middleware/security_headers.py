"""Production security headers (OWASP baseline)."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.services.csp import build_api_csp, generate_nonce


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        nonce = generate_nonce()
        request.state.csp_nonce = nonce

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-XSS-Protection"] = "0"

        if settings.csp_enabled and settings.environment != "development":
            report = settings.csp_report_uri or None
            response.headers["Content-Security-Policy"] = build_api_csp(report_uri=report)
            response.headers["X-CSP-Nonce"] = nonce

        if settings.environment != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
