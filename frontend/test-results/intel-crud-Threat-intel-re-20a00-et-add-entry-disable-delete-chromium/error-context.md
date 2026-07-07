# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: intel-crud.spec.ts >> Threat intel reference set CRUD >> create reference set, add entry, disable, delete
- Location: e2e\intel-crud.spec.ts:9:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: /threat intel/i })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('heading', { name: /threat intel/i })

```

```yaml
- link "Skip to main content":
  - /url: "#main-content"
- complementary:
  - link "Securi home":
    - /url: /
    - img "Securi"
    - paragraph: Securi
    - paragraph: Security Operations
  - navigation "Main navigation":
    - paragraph: Overview
    - link "Dashboard":
      - /url: /
    - link "Analytics":
      - /url: /analytics
    - link "Threat scores":
      - /url: /threat-scores
    - link "Metrics":
      - /url: /metrics
    - paragraph: Operations
    - link "Hosts":
      - /url: /hosts
    - link "Maintenance":
      - /url: /maintenance
    - link "Events":
      - /url: /events
    - link "Alerts":
      - /url: /alerts
    - link "Notifications":
      - /url: /notifications
    - link "Offenses":
      - /url: /offenses
    - link "Case Workspace":
      - /url: /investigation
    - link "Incidents":
      - /url: /incidents
    - paragraph: Intelligence
    - link "MITRE ATT&CK":
      - /url: /mitre
    - link "Timeline":
      - /url: /timeline
    - link "Network":
      - /url: /network
    - link "Search":
      - /url: /search
    - paragraph: Lab
    - link "Attack Lab":
      - /url: /simulation
    - paragraph: Management
    - link "Detection Rules":
      - /url: /rules
    - link "Threat Intel":
      - /url: /intel
    - link "Reports":
      - /url: /reports
    - link "Audit Log":
      - /url: /audit
    - link "System Health":
      - /url: /system
    - paragraph: System
    - link "Settings":
      - /url: /settings
    - link "Profile":
      - /url: /profile
  - text: Live feed connected
  - button "Sign out"
  - button "Collapse sidebar"
- banner:
  - searchbox "Global search"
  - button "Notifications, 84 unread"
  - button "User menu"
  - status:
    - text: "Pilot demo mode — run Multi-Stage Attack in Attack Lab, then follow the guided investigation bar. Demo login: demo@securi.local / Demo1234!"
    - link "Open Attack Lab":
      - /url: /simulation
    - button "Dismiss demo notice"
- main
- button "Open AI Assistant": AI Assistant
- alert
```

# Test source

```ts
  1  | import { test, expect } from "@playwright/test";
  2  | import { loginAsAdmin } from "./helpers/auth";
  3  | 
  4  | const fullStack = !!process.env.E2E_FULL_STACK;
  5  | 
  6  | test.describe("Threat intel reference set CRUD", () => {
  7  |   test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");
  8  | 
  9  |   test("create reference set, add entry, disable, delete", async ({ page }) => {
  10 |     const setName = `e2e_ips_${Date.now()}`;
  11 | 
  12 |     await loginAsAdmin(page);
  13 |     await page.goto("/intel");
> 14 |     await expect(page.getByRole("heading", { name: /threat intel/i })).toBeVisible();
     |                                                                        ^ Error: expect(locator).toBeVisible() failed
  15 | 
  16 |     await page.getByLabel("Name").fill(setName);
  17 |     await page.getByRole("button", { name: "Create set" }).click();
  18 |     await expect(page.getByRole("button", { name: new RegExp(setName) })).toBeVisible({ timeout: 15_000 });
  19 | 
  20 |     await page.getByRole("button", { name: new RegExp(setName) }).click();
  21 |     await page.locator("textarea").fill("203.0.113.50");
  22 |     await page.getByRole("button", { name: /add entries/i }).click();
  23 |     await expect(page.getByText("203.0.113.50")).toBeVisible({ timeout: 15_000 });
  24 | 
  25 |     const card = page.locator("div").filter({ hasText: setName }).first();
  26 |     await card.getByRole("button", { name: "Disable" }).click();
  27 |     await expect(card.getByText(/disabled/)).toBeVisible({ timeout: 10_000 });
  28 | 
  29 |     await card.getByRole("button", { name: "Delete" }).click();
  30 |     await page.getByRole("button", { name: "Delete" }).last().click();
  31 |     await expect(page.getByText(setName)).not.toBeVisible({ timeout: 15_000 });
  32 |   });
  33 | });
  34 | 
```