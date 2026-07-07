import { test, expect } from "@playwright/test";
import { loginAsAdmin } from "./helpers/auth";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("Threat intel reference set CRUD", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("create reference set, add entry, disable, delete", async ({ page }) => {
    const setName = `e2e_ips_${Date.now()}`;

    await loginAsAdmin(page);
    await page.goto("/intel");
    await expect(page.getByText("Threat Intel")).toBeVisible({ timeout: 15_000 });

    await page.getByLabel("Name").fill(setName);
    await page.getByRole("button", { name: "Create set" }).click();
    await expect(page.getByRole("button", { name: new RegExp(setName) })).toBeVisible({ timeout: 15_000 });

    await page.getByRole("button", { name: new RegExp(setName) }).click();
    await page.locator("textarea").fill("203.0.113.50");
    await page.getByRole("button", { name: /add entries/i }).click();
    await expect(page.getByText("203.0.113.50")).toBeVisible({ timeout: 15_000 });

    const card = page.locator("div").filter({ hasText: setName }).first();
    await card.getByRole("button", { name: "Disable" }).click();
    await expect(card.getByText(/disabled/)).toBeVisible({ timeout: 10_000 });

    await card.getByRole("button", { name: "Delete" }).click();
    await page.getByRole("button", { name: "Delete" }).last().click();
    await expect(page.getByText(setName)).not.toBeVisible({ timeout: 15_000 });
  });
});
