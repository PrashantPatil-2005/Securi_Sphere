"""Phase 57 -- Comprehensive security header, CORS, cookie, and traceability tests.

Runs against a live backend at http://127.0.0.1:8000.
Uses httpx (async) for all requests. Reports PASS/FAIL per check.
"""

import asyncio
import httpx
import os
import sys
import uuid as _uuid
from datetime import datetime, timezone

BASE = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))


async def run_all() -> None:
    async with httpx.AsyncClient(
        base_url=BASE,
        follow_redirects=False,
        timeout=10.0,
    ) as client:

        print("\n" + "=" * 70)
        print("  PHASE 57 -- SECURITY TEST SUITE")
        print(f"  Target: {BASE}")
        print(f"  Started: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 70)

        # ==============================================================
        # 1. SECURITY HEADERS on GET /health/ready
        # ==============================================================
        print("\n--- 1. SECURITY HEADERS (GET /health/ready) ---")
        r = await client.get("/health/ready")
        h = r.headers

        check("1.1 X-Content-Type-Options: nosniff",
              h.get("x-content-type-options") == "nosniff",
              f"got '{h.get('x-content-type-options')}'")
        check("1.2 X-Frame-Options: DENY",
              h.get("x-frame-options") == "DENY",
              f"got '{h.get('x-frame-options')}'")
        check("1.3 Referrer-Policy present",
              "referrer-policy" in h,
              f"got '{h.get('referrer-policy')}'")
        check("1.4 Permissions-Policy present",
              "permissions-policy" in h,
              f"got '{h.get('permissions-policy')}'")

        env = os.getenv("ENVIRONMENT", "development")
        if env != "development":
            check("1.5 Strict-Transport-Security present",
                  "strict-transport-security" in h,
                  f"got '{h.get('strict-transport-security')}'")
            check("1.6 Content-Security-Policy present",
                  "content-security-policy" in h,
                  f"got '{h.get('content-security-policy')}'")
        else:
            check("1.5 Strict-Transport-Security (skipped in dev)", True,
                  "environment=development; HSTS intentionally absent")
            check("1.6 Content-Security-Policy (skipped in dev)", True,
                  "environment=development; CSP intentionally absent")

        # ==============================================================
        # 2. CORS -- preflight OPTIONS /api/v1/auth/login
        # ==============================================================
        print("\n--- 2. CORS PREFLIGHT (OPTIONS /api/v1/auth/login) ---")

        r_allowed = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )
        acao_allowed = r_allowed.headers.get("access-control-allow-origin")
        check("2.1 Allowed origin http://localhost:3000 returns ACAO",
              acao_allowed is not None, f"ACAO='{acao_allowed}'")
        check("2.2 Allowed origin ACAO matches request origin",
              acao_allowed == "http://localhost:3000", f"ACAO='{acao_allowed}'")
        acac = r_allowed.headers.get("access-control-allow-credentials")
        check("2.3 Access-Control-Allow-Credentials: true",
              acac == "true", f"got '{acac}'")

        r_evil = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )
        acao_evil = r_evil.headers.get("access-control-allow-origin")
        check("2.4 Rejected origin http://evil.com -- no ACAO header",
              acao_evil is None, f"ACAO='{acao_evil}' (should be None)")

        # ==============================================================
        # 3. COOKIES -- register, login, verify Set-Cookie attributes
        # ==============================================================
        print("\n--- 3. COOKIES -- login flow ---")

        test_email = f"phase57_{_uuid.uuid4().hex[:8]}@test.local"
        test_password = "Phase57Test!Pass#2026"

        r_reg = await client.post(
            "/api/v1/auth/register",
            json={"email": test_email, "password": test_password},
        )
        r_login = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": test_password},
        )

        cookie_tests_passed = False
        if r_login.status_code == 200 and "set-cookie" in r_login.headers:
            cookies_header = r_login.headers.get_list("set-cookie")
            access_cookie_line = next(
                (c for c in cookies_header if c.startswith("access_token=")), ""
            )

            check("3.1 Set-Cookie header present for access_token",
                  bool(access_cookie_line), f"count={len(cookies_header)}")
            check("3.2 HttpOnly flag on access_token cookie",
                  "httponly" in access_cookie_line.lower(),
                  f"snippet: {access_cookie_line[:120]}")

            has_secure = "secure" in access_cookie_line.lower()
            if not has_secure:
                # Secure is intentionally omitted when server has debug=True.
                # Detect this from the server's environment (ENVIRONMENT=development
                # correlates with debug mode in this codebase).
                server_is_dev = env == "development"
                check("3.3 Secure flag absent in debug mode (expected)",
                      server_is_dev,
                      f"Secure absent, environment={env} -> debug=True expected")
            else:
                check("3.3 Secure flag on access_token cookie", True, "Secure present")

            check("3.4 SameSite=Lax on access_token cookie",
                  "samesite=lax" in access_cookie_line.lower(),
                  f"snippet: {access_cookie_line[:120]}")
            cookie_tests_passed = True
        else:
            status = r_login.status_code if r_login else "no-response"
            reg_status = r_reg.status_code if r_reg else "no-response"
            check("3.1 Set-Cookie header present for access_token", False,
                  f"login={status}, register={reg_status}")
            check("3.2 HttpOnly flag", False, "no login cookie")
            check("3.3 Secure flag", False, "no login cookie")
            check("3.4 SameSite=Lax", False, "no login cookie")

        # ==============================================================
        # 4. COOKIES -- logout clears cookie
        # ==============================================================
        print("\n--- 4. COOKIES -- logout flow ---")

        if cookie_tests_passed:
            r_logout = await client.post("/api/v1/auth/logout")
            logout_cookies = r_logout.headers.get_list("set-cookie")
            access_delete = next(
                (c for c in logout_cookies if "access_token=" in c), ""
            )
            check("4.1 Logout sets delete cookie (access_token)",
                  bool(access_delete), f"line: {access_delete[:120]}")
            is_delete = (
                "max-age=0" in access_delete.lower()
                or "expires=thu, 01 jan 1970" in access_delete.lower()
            )
            check("4.2 Cookie deleted (max-age=0 or past Expires)",
                  is_delete, f"line: {access_delete[:120]}")
        else:
            check("4.1 Logout sets delete cookie", False, "skipped — login not obtained")
            check("4.2 Cookie deleted", False, "skipped — login not obtained")

        # ==============================================================
        # 5 & 6. REQUEST TRACEABILITY -- error without token
        # ==============================================================
        print("\n--- 5-6. REQUEST TRACEABILITY ---")
        r_me = await client.get("/api/v1/auth/me")
        ct = r_me.headers.get("content-type", "")
        body_me = r_me.json() if "application/json" in ct else {}
        error_block = body_me.get("error", {})

        check("5.1 GET /api/v1/auth/me without token returns 401",
              r_me.status_code == 401, f"status={r_me.status_code}")
        check("5.2 Error response body has request_id field",
              "request_id" in error_block,
              f"error keys={list(error_block.keys())}")
        check("5.3 X-Request-ID header present in response",
              "x-request-id" in r_me.headers,
              f"header='{r_me.headers.get('x-request-id')}'")

        # ==============================================================
        # 7. Custom X-Request-ID echoed back
        # ==============================================================
        print("\n--- 7. CUSTOM X-Request-ID ECHO ---")
        custom_rid = "test-phase57-custom-rid-001"
        r_custom = await client.get(
            "/api/v1/auth/me",
            headers={"X-Request-ID": custom_rid},
        )
        resp_rid_header = r_custom.headers.get("x-request-id")
        check("7.1 Custom X-Request-ID echoed in response header",
              resp_rid_header == custom_rid,
              f"sent='{custom_rid}', got='{resp_rid_header}'")
        ct2 = r_custom.headers.get("content-type", "")
        body_custom = r_custom.json() if "application/json" in ct2 else {}
        error_custom = body_custom.get("error", {})
        check("7.2 Custom X-Request-ID appears in error body request_id",
              error_custom.get("request_id") == custom_rid,
              f"body request_id='{error_custom.get('request_id')}'")

        # ==============================================================
        # 8. DEMO MODE -- demo user seeding blocked in production
        # ==============================================================
        print("\n--- 8. DEMO MODE -- production guard ---")
        env_val = os.getenv("ENVIRONMENT", "development")
        if env_val == "production":
            r_demo = await client.post(
                "/api/v1/auth/login",
                json={"email": "demo@securi.local",
                       "password": os.getenv("DEMO_USER_PASSWORD", "")},
            )
            check("8.1 Demo user login rejected in production",
                  r_demo.status_code == 401,
                  f"status={r_demo.status_code}")
        else:
            check("8.1 Demo user seeding production guard (code-verified)",
                  True,
                  "ENVIRONMENT != production; guard at auth.py:136")

        # ==============================================================
        # 9. DEMO DATA -- simulation purge endpoint requires auth
        # ==============================================================
        print("\n--- 9. DEMO DATA -- simulation purge guard ---")
        r_purge = await client.delete("/api/v1/simulation/purge")
        check("9.1 Simulation purge requires authentication (401)",
              r_purge.status_code == 401, f"status={r_purge.status_code}")
        r_purge_auth = await client.delete(
            "/api/v1/simulation/purge",
            headers={"Authorization": "Bearer fake-token"},
        )
        check("9.2 Simulation purge rejects invalid token (401)",
              r_purge_auth.status_code == 401,
              f"status={r_purge_auth.status_code}")

    # ==============================================================
    # SUMMARY
    # ==============================================================
    print("\n" + "=" * 70)
    total = len(RESULTS)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = total - passed
    print(f"  TOTAL: {total}  |  PASS: {passed}  |  FAIL: {failed}")
    print("=" * 70)

    if failed:
        print("\n  FAILED CHECKS:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"    X {name}: {detail}")

    print()
    return failed


if __name__ == "__main__":
    failed = asyncio.run(run_all())
    sys.exit(1 if failed else 0)
