# Securi Frontend

Next.js 14 App Router dashboard for the Securi SIEM platform.

## Dev setup

```powershell
cd frontend
npm install
# Ensure backend is running on :8000; API is proxied via next.config.mjs rewrites
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` when running `npm run build` / production start without the dev proxy.

Or use the repo root script: `.\scripts\dev-windows.ps1`

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm run lint` | ESLint |
| `npx tsc --noEmit` | Typecheck |
| `npm run test:e2e` | Playwright smoke (pages load) |
| `E2E_FULL_STACK=1 npm run test:e2e` | Full SOC lab + invite E2E (needs backend) |

## E2E tests

- `e2e/smoke.spec.ts` — login/register page load
- `e2e/lab-flow.spec.ts` — SOC lab (requires `E2E_FULL_STACK=1`)
- `e2e/invite-flow.spec.ts` — invite acceptance (requires `E2E_FULL_STACK=1`)
