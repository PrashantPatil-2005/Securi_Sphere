import { test, expect } from "@playwright/test";
import { dismissBlockingOverlays, loginAsAdmin } from "./helpers/auth";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("SOC lab flow", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("golden path: login → simulation → alerts → offenses → case workspace → timeline", async ({ page }) => {
    test.setTimeout(120_000);
    await loginAsAdmin(page);

    await page.goto("/simulation");
    await dismissBlockingOverlays(page);
    await expect(page.getByRole("heading", { name: "Attack Simulation Lab" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Presets" })).toBeVisible();
    await page.getByRole("button", { name: /run simulation/i }).click();
    await expect(page.getByRole("heading", { name: /simulation complete/i })).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("p", { hasText: /^Guided investigation$/ })).toBeVisible();

    await page.getByRole("link", { name: /triage alerts/i }).first().click();
    await expect(page).toHaveURL(/\/alerts/);
    await expect(page.locator(".data-table-row").first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/offenses");
    await expect(page.getByRole("heading", { name: "Offense Management" })).toBeVisible();
    await page.getByRole("button", { name: /events/i }).first().click({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: "Open Case Workspace" })).toBeVisible();

    await page.getByRole("link", { name: "Open Case Workspace" }).click();
    await expect(page).toHaveURL(/\/investigation/);
    await expect(page.getByRole("heading", { name: "Case Workspace" })).toBeVisible();
    await expect(page.getByText("Next actions")).toBeVisible();

    await page.goto("/timeline");
    await expect(page.getByRole("heading", { name: "Attack Timelines" })).toBeVisible({ timeout: 15_000 });

    await page.goto("/simulation");
    await page.getByRole("tab", { name: "Custom" }).click();
    await page.getByRole("button", { name: /run custom simulation/i }).click();
    await expect(page.getByRole("heading", { name: /simulation complete/i })).toBeVisible({ timeout: 30_000 });

    await page.getByRole("tab", { name: "History" }).click();
    await expect(page.getByText("Run history")).toBeVisible();
    await expect(page.getByText("Custom attack chain").or(page.getByText(/custom/i)).first()).toBeVisible({
      timeout: 10_000,
    });
  });
});
