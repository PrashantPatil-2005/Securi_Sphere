# Content-Security-Policy (CSP) with nonces

Per-request nonces tighten script/style execution without blanket `unsafe-inline` in production.

## Frontend (Next.js)

`middleware.ts` generates a cryptographically random nonce on each page request and:

1. Sets `Content-Security-Policy` on the response
2. Passes `x-nonce` to the app via request headers
3. `ThemeScript` applies `nonce={...}` to the inline boot script

Production `script-src`: `'self' 'nonce-{nonce}' 'strict-dynamic'`

Development keeps `'unsafe-eval'` / `'unsafe-inline'` for Next.js hot reload.

### Optional reporting

```env
CSP_REPORT_URI=https://your-collector.example/csp
```

## Backend (FastAPI API)

`SecurityHeadersMiddleware` uses `app/services/csp.py` to set a strict API CSP in non-development environments:

```
default-src 'none'; frame-ancestors 'none'; ...
```

No inline scripts on JSON responses — nonces are exposed as `X-CSP-Nonce` for observability.

### Configuration

```env
CSP_ENABLED=true
CSP_REPORT_URI=
ENVIRONMENT=production
```

## Verify

1. Open the dashboard in production build (`npm run build && npm start`)
2. DevTools → Network → document response headers → `Content-Security-Policy` includes `nonce-`
3. View page source → theme `<script nonce="...">`
