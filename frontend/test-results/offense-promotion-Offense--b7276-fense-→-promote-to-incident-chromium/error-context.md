# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: offense-promotion.spec.ts >> Offense promotion flow >> simulation → offense → promote to incident
- Location: e2e\offense-promotion.spec.ts:10:7

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected: "http://127.0.0.1:3000/"
Received: "http://127.0.0.1:3000/login"
Timeout:  30000ms

Call log:
  - Expect "toHaveURL" with timeout 30000ms
    63 × unexpected value "http://127.0.0.1:3000/login"

```

```yaml
- heading "Securi" [level=1]
- paragraph: Enterprise Security Platform
- blockquote: Unified security operations for modern enterprises. Monitor, detect, and respond — in real time.
- paragraph: 99.9%
- paragraph: Uptime SLA
- paragraph: <2s
- paragraph: Detection Latency
- paragraph: 24/7
- paragraph: Monitoring
- paragraph: © 2026 Securi. All rights reserved.
- heading "Sign in" [level=1]
- paragraph: Access your security operations center
- alert: Rate limit exceeded
- text: Email address
- textbox "Email address":
  - /placeholder: you@company.com
  - text: admin@test.local
- text: Password
- link "Forgot password?":
  - /url: /forgot-password
- textbox "Password": testpass123
- button "Sign in"
- paragraph:
  - text: Don't have an account?
  - link "Create account":
    - /url: /register
- alert
```

# Test source

```ts
  1  | import { expect, type Page } from "@playwright/test";
  2  | 
  3  | /** Sign in through the login form (works with split frontend/API hosts). */
  4  | export async function loginAsAdmin(page: Page) {
  5  |   await page.goto("/login");
  6  |   await page.getByLabel("Email address").fill("admin@test.local");
  7  |   await page.locator("#password").fill("testpass123");
  8  |   await page.getByRole("button", { name: /sign in/i }).click();
> 9  |   await expect(page).toHaveURL("/", { timeout: 30_000 });
     |                      ^ Error: expect(page).toHaveURL(expected) failed
  10 | }
  11 | 
  12 | export async function addHost(page: Page, hostName: string) {
  13 |   await page.goto("/hosts");
  14 |   await page.getByPlaceholder("New host name").fill(hostName);
  15 |   await page.getByRole("button", { name: "Add host" }).click();
  16 |   await expect(page.getByText(hostName).first()).toBeVisible({ timeout: 15_000 });
  17 | }
  18 | 
```