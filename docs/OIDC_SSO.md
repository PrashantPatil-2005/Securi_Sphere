# OIDC / SSO — Securi

Enterprise login via OpenID Connect (Google Workspace, Azure AD, Okta, etc.) alongside existing email/password auth.

## Enable

```env
OIDC_ENABLED=true
OIDC_ISSUER_URL=https://accounts.google.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_PROVIDER_LABEL=Google
OIDC_AUTO_PROVISION=false
OIDC_DEFAULT_ROLE=analyst
```

### Azure AD app roles

Use the `roles` claim instead of `groups`:

```env
OIDC_GROUPS_CLAIM=roles
OIDC_ROLE_MAP={"Securi.Admin":"admin","Securi.Analyst":"analyst","Securi.Viewer":"viewer"}
OIDC_SYNC_ROLES_ON_LOGIN=true
```

### Domain allowlist (auto-provision)

Restrict which email domains can be auto-created:

```env
OIDC_AUTO_PROVISION=true
OIDC_ALLOWED_EMAIL_DOMAINS=company.com,subsidiary.com
```

Leave empty to allow any domain when auto-provision is on.

Run migration:

```bash
cd backend
alembic upgrade head
```

## Redirect URI

Register this callback URL with your identity provider:

```
{SERVER_URL}/api/v1/auth/oidc/callback
```

Example: `http://localhost:8000/api/v1/auth/oidc/callback`

## Flow

1. User clicks **Sign in with SSO** on `/login`
2. `GET /api/v1/auth/oidc/login?next=/alerts` → redirect to IdP
3. IdP returns to `/api/v1/auth/oidc/callback`
4. Backend validates `id_token` (JWKS), links or provisions user, sets HttpOnly JWT cookies
5. Redirect to `{FRONTEND_URL}{next}`

## User linking

| Case | Behavior |
|------|----------|
| User exists with matching `oidc_sub` + issuer | Login |
| User exists with same email, no OIDC link | Link OIDC identity to account |
| Admin must invite/create user first | Use **Settings → Team** or `POST /api/v1/users` |
| No user, `OIDC_AUTO_PROVISION=true` | Create user; role from `OIDC_ROLE_MAP` or `OIDC_DEFAULT_ROLE` |
| Existing SSO user on login | Role synced from IdP groups when `OIDC_SYNC_ROLES_ON_LOGIN=true` |
| First user in empty DB | Gets `admin` role (same as local register) |

SSO-only users have no local password; password change is blocked.

## Provider examples

### Google

```env
OIDC_ISSUER_URL=https://accounts.google.com
OIDC_PROVIDER_LABEL=Google
```

### Azure AD

```env
OIDC_ISSUER_URL=https://login.microsoftonline.com/{tenant-id}/v2.0
OIDC_PROVIDER_LABEL=Microsoft
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/auth/oidc/login` | Start OIDC flow |
| `GET /api/v1/auth/oidc/callback` | IdP callback (do not call manually) |
| `GET /api/v1/settings/public` | Returns `oidc_enabled`, `oidc_provider_label` |

## Security notes

- State + nonce stored in signed JWT (10 min TTL)
- `id_token` validated against IdP JWKS (`aud`, `iss`, `nonce`)
- Keep `OIDC_AUTO_PROVISION=false` in production until `OIDC_ROLE_MAP` and `OIDC_ALLOWED_EMAIL_DOMAINS` are configured
- SAML is not implemented — use an OIDC bridge (e.g. Azure AD OIDC) if needed

## Files

| Path | Role |
|------|------|
| `app/services/oidc.py` | Discovery, token exchange, user resolution |
| `app/services/oidc_roles.py` | Group → role mapping, domain allowlist |
| `app/routers/oidc.py` | Login + callback routes |
| `app/services/auth_session.py` | Shared JWT cookie issuance |
| `alembic/versions/007_oidc_users.py` | `oidc_sub`, `oidc_issuer` columns |
