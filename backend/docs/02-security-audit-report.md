# 2. Security Audit Report

## Executive Summary

Pre-refactor security posture was adequate for development but had critical gaps for production deployment. This report catalogs findings and remediation status.

**Risk Level (Pre-Refactor):** Medium-High  
**Risk Level (Post-Refactor):** Medium (acceptable for controlled deployment)

---

## Authentication & Authorization

### JWT Implementation

| Control | Before | After | Status |
|---------|--------|-------|--------|
| Access token expiry (15 min) | ✓ | ✓ | OK |
| Refresh token rotation | ✓ | ✓ Enhanced with session tracking | OK |
| Refresh token revocation | Partial (delete on rotate) | Session table with revoke | Improved |
| Token type validation | ✓ | ✓ | OK |
| HS256 symmetric signing | ✓ | ✓ | **Migrate to RS256 in prod** |
| Role-based access control | ✓ | ✓ | OK |

### Findings

| ID | Finding | Severity | Remediation |
|----|---------|----------|-------------|
| SEC-001 | No account lockout | High | **Fixed** — 5 attempts, 15 min lockout |
| SEC-002 | No session/device tracking | Medium | **Fixed** — `user_sessions` table |
| SEC-003 | Registration open to anyone | High | **Open** — disable in prod or require invite |
| SEC-004 | First user auto-admin | Medium | Acceptable for bootstrap; document |
| SEC-005 | Password reset tokens not rate-limited | Medium | **Open** — add per-email limit |
| SEC-006 | JWT secret in env only | Medium | Use secrets manager (Vault/K8s secrets) |

---

## Agent Security

### API Key Authentication

| Control | Before | After |
|---------|--------|-------|
| Hashed storage (SHA-256) | ✓ | ✓ |
| Key rotation endpoint | ✗ | **Added** `POST /agent/rotate-key` |
| Key revocation | ✗ | **Added** `api_key_revoked_at` |
| Enrollment token single-use | ✓ | ✓ |
| Enrollment token expiry | ✓ | ✓ |
| Enrollment token revocation | ✓ | ✓ |

### Request Signing & Replay Protection

| Control | Status |
|---------|--------|
| HMAC-SHA256 request signing | **Implemented** (opt-in via `AGENT_REQUEST_SIGNING`) |
| Timestamp validation (±5 min) | **Implemented** |
| Nonce/replay store | **Implemented** — `agent_request_nonces` |
| mTLS agent transport | **Not implemented** — recommended for Phase 2 |

**Agent Security Headers (when signing enabled):**
```
X-Agent-Timestamp: 2026-06-21T12:00:00Z
X-Agent-Nonce: <unique-per-request>
X-Agent-Signature: HMAC-SHA256(api_key, timestamp.nonce.body)
```

---

## API Security

| Control | Before | After |
|---------|--------|-------|
| Rate limiting | Auth only (20/min) | Auth + Agent (120/min) |
| CORS | Frontend URL + localhost | Same — tighten for prod |
| Input validation | Pydantic schemas | + pipeline validator |
| SQL injection | SQLAlchemy ORM | OK |
| Structured errors | Plain detail strings | Structured JSON with request_id |
| Audit logging | Partial | Existing audit service |
| HTTPS enforcement | Not in app | **Deploy behind TLS terminator** |

### Unauthenticated Endpoints (Review Required)

| Endpoint | Risk | Action |
|----------|------|--------|
| `GET /health` | Low | OK |
| `GET /api/v1/overview` | Medium | Restrict in prod |
| `GET /install.sh` | Low | OK |
| `POST /auth/register` | High | Disable or gate |
| `POST /auth/forgot-password` | Medium | Rate limit per email |

---

## Data Security

| Area | Finding | Recommendation |
|------|---------|----------------|
| Password storage | bcrypt | OK |
| API key storage | SHA-256 hash | OK — consider pepper |
| PII in events | username, source_ip stored | Define retention policy |
| Audit logs | Append-only + hash chain | `docs/IMMUTABLE_AUDIT_STORE.md` |
| Database encryption | Not in app | `docs/DB_ENCRYPTION_AT_REST.md` |
| Secrets in .env | Required | Move to secrets manager |

---

## WebSocket Security

- JWT validated on connect ✓
- No message-level auth after connect — acceptable for read-only feed
- **Recommendation:** Rate limit WS connections per user

---

## Dependency Vulnerabilities

Run regularly:
```bash
pip audit
# or
safety check -r requirements.txt
```

Pin and update: `python-jose`, `passlib`, `fastapi`, `sqlalchemy`

---

## Security Hardening Checklist (Production)

- [ ] Disable public registration
- [ ] RS256 JWT with key rotation
- [ ] Enable `AGENT_REQUEST_SIGNING=true`
- [ ] mTLS between agent and API
- [ ] WAF in front of API
- [ ] Network segmentation (agents → ingest VLAN only)
- [ ] PostgreSQL SSL + least-privilege DB user
- [ ] Secrets in Vault/AWS Secrets Manager
- [ ] SIEM the SIEM (forward audit logs to external SIEM)
