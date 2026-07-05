import { test, expect } from "@playwright/test";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("SOC lab flow", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("register → host → simulation → alerts", async ({ page }) => {
    const stamp = Date.now();
    const email = `e2e-${stamp}@test.local`;
    const password = "testpass123";
    const hostName = `lab-host-${stamp}`;

    await page.goto("/register");
    await page.getByLabel("Email address").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByLabel("Confirm password").fill(password);
    await page.getByRole("button", { name: /create account/i }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel("Email address").fill(email);
    await page.locator("#password").fill(password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL("/");

    await page.goto("/hosts");
    await page.getByPlaceholder("New host name").fill(hostName);
    await page.getByRole("button", { name: "Add host" }).click();
    await expect(page.getByText(hostName)).toBeVisible({ timeout: 15_000 });

    await page.goto("/simulation");
    await expect(page.getByRole("heading", { name: "Attack Simulation" })).toBeVisible();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: /run simulation/i }).click();
    await expect(page.getByText(/events injected/i)).toBeVisible({ timeout: 30_000 });

    await page.goto("/alerts");
    await expect(page.getByRole("heading", { name: "Alerts" })).toBeVisible();
    const alertRows = page.locator(".alert-row");
    await expect(alertRows.first()).toBeVisible({ timeout: 30_000 });
  });
});
