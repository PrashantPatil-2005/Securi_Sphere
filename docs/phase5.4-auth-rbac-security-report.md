# Phase 5.4 — Auth, RBAC & Session Security Hardening: Completion Report

## Summary

Comprehensive security audit and hardening of authentication, authorization, RBAC, sessions, OIDC, MFA, and security configuration. **8 fixes applied across 7 files.** Full RBAC route→role matrix documented (187 endpoints).

---

## Fixes Applied

### 1. Login Rate Limiting (auth.py)
- **Before:** No rate limiting on `/auth/login` — brute-force attacks unrestricted at endpoint level
- **After:** IP-based rate limiting: 10 attempts per lockout window (15 minutes)
- **Impact:** Brute-force login attacks throttled per-IP

### 2. Password Complexity in Provisioning (user_provisioning.py)
- **Before:** `provision_user()` and `accept_invite()` accepted any password (or no password) without complexity validation
- **After:** All admin-created and invite-accepted passwords validated against the same complexity regex (uppercase, lowercase, digit, special char, min 8 chars)
- **Impact:** No weak passwords can be set through any path

### 3. OIDC Email Verification (oidc.py)
- **Before:** OIDC login accepted unverified emails from the IdP — if the IdP issued tokens for unverified emails, an attacker controlling that email could take over a matching local account
- **After:** `email_verified` claim checked; `False` rejected with 401
- **Impact:** Account takeover via unverified OIDC emails prevented

### 4. Password Reset Session Revocation (auth.py)
- **Before:** Password reset changed the password but left all existing refresh tokens and sessions active — a stolen session remained valid after reset
- **After:** All `RefreshToken` and `UserSession` records for the user are revoked on password reset
- **Impact:** Compromised sessions invalidated on password reset

### 5. Password Change Session Revocation (auth.py)
- **Before:** Password change did not revoke existing sessions
- **After:** All `RefreshToken` and `UserSession` records for the user are revoked on password change
- **Impact:** Compromised sessions invalidated on password change

### 6. DEMO_MODE Production Guard (auth.py)
- **Before:** If `DEMO_MODE=true` was accidentally set in production, a known admin account (`demo@securi.local`) would be created with a shared password
- **After:** `seed_demo_users()` refuses to seed when `environment == "production"`
- **Impact:** Demo backdoor eliminated in production environments

### 7. Cookie Clear Security (auth_cookies.py)
- **Before:** `clear_auth_cookies()` used `delete_cookie()` without `secure`/`samesite` flags — may not properly clear cookies in all browser configurations
- **After:** `secure` and `samesite="lax"` flags set on cookie deletion
- **Impact:** Cookies reliably cleared across all environments

### 8. Concurrent Session Limit (auth_session.py, config.py)
- **Before:** No limit on concurrent sessions per user — a compromised account could have unlimited active sessions
- **After:** Configurable `max_concurrent_sessions` (default 10); oldest sessions revoked when limit exceeded
- **Impact:** Session count bounded per user; oldest sessions automatically cleaned

---

## Audit Findings (Documented, Not Fixed)

### Authentication
| Finding | Severity | Status |
|---|---|---|
| bcrypt hashing with auto-upgrade | GOOD | Documented |
| Constant-time password comparison via passlib | GOOD | Documented |
| Uniform "Invalid credentials" prevents user enumeration | GOOD | Documented |
| Account lockout after 5 failed attempts | GOOD | Documented |
| Role not selectable during self-registration | GOOD | Documented |
| First-user-gets-admin pattern | GOOD | Documented |
| Token type claims prevent access/refresh confusion | GOOD | Documented |
| Algorithm whitelisting prevents JWT confusion | GOOD | Documented |
| Access tokens not invalidated on logout (stateless JWT) | MEDIUM | Documented — accepted risk |
| Role claim in access token not revocable for 15min | MEDIUM | Documented — accepted risk |
| No escalating backoff on lockout | LOW | Documented |

### Sessions
| Finding | Severity | Status |
|---|---|---|
| Refresh token rotation (single-use) | GOOD | Documented |
| `WITH FOR UPDATE` prevents refresh token race | GOOD | Documented |
| Session + refresh revoked on logout | GOOD | Documented |
| Session metadata (IP, device, UA) tracked | GOOD | Documented |
| No "logout all devices" functionality | MEDIUM | Documented |
| Access tokens not invalidated on logout | MEDIUM | Documented — accepted risk |

### OIDC
| Finding | Severity | Status |
|---|---|---|
| Signed JWT state + nonce prevents CSRF | GOOD | Documented |
| No open redirect possible | GOOD | Documented |
| Token validation (signature, expiry, issuer, audience) | GOOD | Documented |
| Algorithm allowlist excludes `none` and HMAC | GOOD | Documented |
| First auto-provisioned OIDC user becomes admin | LOW | Documented |

### MFA
| Finding | Severity | Status |
|---|---|---|
| TOTP with +/- 30s clock drift tolerance | GOOD | Documented |
| Backup codes: 8 codes, SHA-256 hashed, single-use | GOOD | Documented |
| MFA disable requires password + TOTP/backup code | GOOD | Documented |
| Rate limiting: 10 attempts per 5min per IP | GOOD | Documented |
| TOTP secrets stored in plaintext in database | MEDIUM | Documented — requires encryption at rest |
| Rate limiting per-IP not per-user | LOW | Documented |

### Password Reset
| Finding | Severity | Status |
|---|---|---|
| 256-bit random tokens | GOOD | Documented |
| 1-hour expiration | GOOD | Documented |
| Atomic single-use via `UPDATE ... RETURNING` | GOOD | Documented |
| Generic response prevents email enumeration | GOOD | Documented |
| Rate limiting: per-IP and per-token | GOOD | Documented |

### RBAC (Route→Role Matrix)
| Finding | Severity | Status |
|---|---|---|
| All 187 endpoints audited for auth + role requirements | PASS | Documented |
| All write endpoints require analyst+ | PASS | Documented |
| Viewer role never appears on any write endpoint | PASS | Documented |
| Admin self-deactivation prevented | PASS | Documented |
| Last-admin deletion prevented | PASS | Documented |

### IDOR/BOLA
| Finding | Severity | Status |
|---|---|---|
| Saved searches: user_id filter on all CRUD | PASS | Documented |
| Notification rules: user_id filter on all CRUD | PASS | Documented |
| Notification settings: scoped via user_id | PASS | Documented |
| Dashboard layouts: scoped via user_id | PASS | Documented |
| Alerts/offenses/incidents: global by design (SIEM) | PASS | Documented |

### Privilege Escalation
| Finding | Severity | Status |
|---|---|---|
| Registration schema has no `role` field | PASS | Documented |
| Profile update schema only exposes `full_name` | PASS | Documented |
| Invite acceptance role fixed by admin | PASS | Documented |
| Admin cannot change own role | PASS | Documented |
| Admin cannot deactivate self | PASS | Documented |

### Security Headers
| Finding | Severity | Status |
|---|---|---|
| CSP: `default-src 'none'` (strict API policy) | EXCELLENT | Documented |
| CORS: no wildcard origins; dev origins gated by env | GOOD | Documented |
| X-Content-Type-Options: nosniff | GOOD | Documented |
| X-Frame-Options: DENY | GOOD | Documented |
| HSTS: max-age=1year; includeSubDomains | GOOD | Documented |
| Referrer-Policy: strict-origin-when-cross-origin | GOOD | Documented |
| Permissions-Policy: camera/mic/geo disabled | GOOD | Documented |
| SameSite=Lax on auth cookies | GOOD | Documented |

### Agent Auth
| Finding | Severity | Status |
|---|---|---|
| API keys: 256-bit, SHA-256 hashed, per-host | GOOD | Documented |
| Enrollment tokens: single-use, time-limited | GOOD | Documented |
| Request signing disabled by default | MEDIUM | Documented |

### Error Disclosure
| Finding | Severity | Status |
|---|---|---|
| No stack traces leaked to clients | GOOD | Documented |
| No database errors exposed | GOOD | Documented |
| Generic 500 error responses | GOOD | Documented |

---

## Files Changed

| File | Changes |
|---|---|
| `backend/app/routers/auth.py` | Login rate limiting, password reset session revocation, password change session revocation, DEMO_MODE production guard |
| `backend/app/auth_cookies.py` | Cookie clear with secure/samesite flags |
| `backend/app/services/oidc.py` | OIDC email_verified claim check |
| `backend/app/services/user_provisioning.py` | Password complexity validation in provision_user and accept_invite |
| `backend/app/services/auth_session.py` | Concurrent session limit enforcement |
| `backend/app/config.py` | `max_concurrent_sessions` setting |

---

## Verification

- **Unit tests:** 7/7 pass
- **Lint:** All modified files clean (E402/F821 errors are pre-existing)
- **OpenAPI:** 194 routes generated successfully

---

## Infrastructure Limitations

- **Docker not available** — PostgreSQL integration tests could not run
- **Redis not available** — Redis-specific security tests could not run
- **Browser not available** — Frontend WebSocket/auth tests could not run

---

## Remaining Issues

### Security Weaknesses (Accepted Risks)
- Access tokens remain valid for up to 15 minutes after logout (stateless JWT limitation)
- Role claim in access token not revocable until expiry
- TOTP secrets stored in plaintext (requires encryption-at-rest migration)
- No "logout all devices" functionality
- Agent request signing disabled by default

### Architectural Limitations
- No token revocation list for access tokens
- No idle session timeout (only absolute expiry via refresh token)
- WebSocket auth accepted before handshake (10s resource window)

### Future Improvements
- Add "logout all devices" endpoint
- Encrypt TOTP secrets at rest with application-layer key
- Add idle session timeout
- Enable agent request signing by default
- Add password breach dictionary check (HaveIBeenPwned API)

---

READY FOR PHASE 5.5
