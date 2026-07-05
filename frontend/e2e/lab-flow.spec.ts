import { test, expect } from "@playwright/test";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("SOC lab flow", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("admin login → host → simulation → alerts", async ({ page }) => {
    const stamp = Date.now();
    const hostName = `lab-host-${stamp}`;

    await page.goto("/login");
    await page.getByLabel("Email address").fill("admin@test.local");
    await page.locator("#password").fill("testpass123");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL("/");

    await page.goto("/hosts");
    await page.getByPlaceholder("New host name").fill(hostName);
    await page.getByRole("button", { name: "Add host" }).click();
    await expect(page.getByText(hostName)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(hostName).locator("..").locator("..")).toContainText(/inactive|offline/i);

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
