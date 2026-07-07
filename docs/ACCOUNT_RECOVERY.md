# Account recovery rate limits

Protects password reset and MFA verification from abuse.

## Limits (defaults)

| Action | Key | Default limit | Window |
|--------|-----|---------------|--------|
| Forgot password | Per IP | 5 | 1 hour |
| Forgot password | Per email | 3 | 1 hour |
| Reset password | Per IP | 15 | 1 hour |
| Reset password failures | Per token | 5 | 15 min |
| MFA verify | Per IP | 10 | 5 min |

General `/api/v1/auth` middleware limit (20/min per IP) still applies.

## Configuration

```env
RECOVERY_FORGOT_IP_LIMIT=5
RECOVERY_FORGOT_IP_WINDOW_SECONDS=3600
RECOVERY_FORGOT_EMAIL_LIMIT=3
RECOVERY_FORGOT_EMAIL_WINDOW_SECONDS=3600
RECOVERY_RESET_IP_LIMIT=15
RECOVERY_RESET_IP_WINDOW_SECONDS=3600
RECOVERY_RESET_TOKEN_FAIL_LIMIT=5
RECOVERY_RESET_TOKEN_FAIL_WINDOW_SECONDS=900
RECOVERY_MFA_IP_LIMIT=10
RECOVERY_MFA_IP_WINDOW_SECONDS=300
```

## Behavior

- **Forgot password** — rate check runs before user lookup (same response whether account exists)
- **Reset password** — IP limit on every attempt; invalid tokens increment per-token failure counter
- **MFA verify** — IP limit on each code submission

Uses Redis sliding windows when `REDIS_URL` is set; otherwise in-memory (single process).

## API response

HTTP `429` with `Retry-After` header and message: `Too many recovery attempts. Please try again later.`
