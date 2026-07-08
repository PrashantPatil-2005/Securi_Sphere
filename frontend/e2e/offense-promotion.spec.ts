import { test, expect } from "@playwright/test";
import { addHost, loginAsAdmin } from "./helpers/auth";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("Offense promotion flow", () => {
  test.describe.configure({ timeout: 120_000 });
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("simulation → offense → promote to incident", async ({ page }) => {
    const hostName = `promote-host-${Date.now()}`;

    await loginAsAdmin(page);
    await addHost(page, hostName);

    await page.goto("/simulation");
    await page.getByRole("button", { name: /run simulation/i }).click();
    await expect(page.getByText(/simulation complete/i)).toBeVisible({ timeout: 30_000 });

    await page.goto("/offenses");
    await expect(page.getByRole("heading", { name: /offense management/i })).toBeVisible();
    const offenseItem = page.locator("button").filter({ hasText: /^#\d+/ }).first();
    await expect(offenseItem).toBeVisible({ timeout: 45_000 });
    await offenseItem.click();

    await page.getByRole("button", { name: "Promote to incident" }).click();
    await expect(page.getByRole("button", { name: /view in case workspace/i })).toBeVisible({ timeout: 45_000 });

    await page.goto("/incidents");
    await expect(page.getByRole("heading", { name: /incidents/i, level: 1 })).toBeVisible();
  });
});
