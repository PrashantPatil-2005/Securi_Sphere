# Onboarding wizard

First-run guided tour for new analysts. Complements the dashboard **Getting started** checklist with a modal walkthrough.

## Behavior

- Opens automatically on first authenticated session when onboarding is incomplete (`completedCount < totalSteps`).
- Persists skip state in `localStorage` key `securi_onboarding_wizard_done`.
- Re-open from the dashboard checklist via **Open setup wizard**.
- Auto-closes and marks complete when all checklist steps are done.

## Steps

The wizard mirrors `ONBOARDING_STEPS` in `frontend/lib/hooks/useOnboardingProgress.ts`:

| Step | Route | Completion signal |
|------|-------|-------------------|
| Host (optional) | `/hosts` | `total_hosts >= 1` |
| Attack Lab | `/simulation` | `simulation/runs` total ≥ 1 |
| Triage alert | `/alerts` | Any investigating or resolved alert |
| Offense → incident | `/offenses` | At least one incident |
| SIEM search | `/search` | `securi_onboarding_search` localStorage flag |
| Notifications | `/settings` | Email, Slack, or Telegram enabled |

Progress is polled from existing API endpoints (overview, alerts, offenses, incidents, notification settings).

## Components

- `frontend/components/onboarding/OnboardingWizard.tsx` — modal wizard (mounted in `AppShell`)
- `frontend/components/OnboardingChecklist.tsx` — persistent checklist widget + wizard trigger
- `frontend/lib/onboarding.ts` — dismiss / reopen helpers

## Testing locally

1. Clear wizard state: `localStorage.removeItem('securi_onboarding_wizard_done')`
2. Sign in and land on `/` — wizard should appear if steps remain incomplete.
3. Use **Skip tour** or complete all steps to dismiss permanently.
