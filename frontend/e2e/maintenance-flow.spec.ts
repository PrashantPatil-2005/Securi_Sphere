import { test, expect } from "@playwright/test";
import { addHost, loginAsAdmin } from "./helpers/auth";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("Maintenance windows flow", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("schedule and remove a maintenance window", async ({ page }) => {
    const stamp = Date.now();
    const hostName = `maint-host-${stamp}`;
    const reason = `patch-${stamp}`;

    await loginAsAdmin(page);
    await addHost(page, hostName);

    await page.goto("/maintenance");
    await expect(page.getByRole("heading", { name: /maintenance windows/i })).toBeVisible();

    await page.getByLabel("Host").selectOption({ label: hostName });
    await page.getByLabel("Reason (optional)").fill(reason);
    await page.getByRole("button", { name: /create window/i }).click();

    await expect(page.locator("span.font-medium", { hasText: hostName })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(reason)).toBeVisible();
    await expect(page.getByText(/active/i).first()).toBeVisible();

    await page.getByRole("button", { name: new RegExp(`Remove maintenance window for ${hostName}`, "i") }).click();
    await expect(page.getByText(reason)).not.toBeVisible({ timeout: 15_000 });
  });
});
