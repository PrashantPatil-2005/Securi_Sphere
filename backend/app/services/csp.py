"""Content-Security-Policy helpers with per-request nonces."""

import secrets


def generate_nonce() -> str:
    return secrets.token_urlsafe(16)


def build_api_csp(*, report_uri: str | None = None) -> str:
    """Strict CSP for JSON API responses (no inline scripts)."""
    parts = [
        "default-src 'none'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ]
    if report_uri:
        parts.append(f"report-uri {report_uri}")
    return "; ".join(parts)


def build_html_csp(nonce: str, *, report_uri: str | None = None) -> str:
    """CSP for HTML pages when the backend serves markup."""
    parts = [
        "default-src 'self'",
        f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic'",
        f"style-src 'self' 'nonce-{nonce}'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "object-src 'none'",
    ]
    if report_uri:
        parts.append(f"report-uri {report_uri}")
    return "; ".join(parts)
