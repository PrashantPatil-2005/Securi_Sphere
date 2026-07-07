# Multi-factor authentication (TOTP)

Securi supports **TOTP** (RFC 6238) via authenticator apps (Google Authenticator, Authy, 1Password, etc.).

## Setup (Profile)

1. **Profile → Two-factor authentication → Set up authenticator**
2. Scan or copy the secret into your app
3. Enter the 6-digit code to enable
4. **Save backup codes** — single-use recovery if you lose the device

## Login flow

1. Email + password as usual
2. If MFA is enabled, enter **6-digit TOTP** or a **backup code**
3. Session cookies are issued after successful verification

## API

```
GET  /api/v1/auth/mfa/status
POST /api/v1/auth/mfa/setup
POST /api/v1/auth/mfa/enable   { "code": "123456" }
POST /api/v1/auth/mfa/disable  { "code": "...", "password": "..." }
POST /api/v1/auth/mfa/verify   { "mfa_token": "...", "code": "..." }
```

`POST /auth/login` returns `mfa_required: true` and `mfa_token` when MFA is enabled (no session until verify).

## Migration

```bash
cd backend && alembic upgrade head
```

Revision `014_user_mfa`.

## Dependency

`pyotp` — add to backend requirements.
