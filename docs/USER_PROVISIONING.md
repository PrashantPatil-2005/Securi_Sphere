# Admin user provisioning

Pre-provision analysts before SSO (`OIDC_AUTO_PROVISION=false`) or lock down open registration.

## Admin UI

**Settings → Team** (admin only):

- **Email invite** — sends link to `/accept-invite?token=...`
- **Direct provision** — creates user immediately (SSO-only or with password)
- Manage roles and enable/disable accounts

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/users` | List users (admin) |
| POST | `/api/v1/users` | Provision user directly |
| PATCH | `/api/v1/users/{id}` | Change role or `is_active` |
| GET | `/api/v1/users/invites` | Pending invites |
| POST | `/api/v1/users/invites` | Send invite email |
| DELETE | `/api/v1/users/invites/{id}` | Revoke invite |
| GET | `/api/v1/users/invites/preview?token=` | Public invite preview |
| POST | `/api/v1/users/invites/accept` | Public — create account |

### Provision SSO-only user

```http
POST /api/v1/users
{
  "email": "analyst@company.com",
  "role": "analyst",
  "full_name": "Alex Analyst",
  "sso_only": true
}
```

User can sign in via OIDC once their IdP account matches the email.

## Migration

```bash
cd backend && alembic upgrade head
```

Creates `user_invites` table (revision `008_user_invites`).
