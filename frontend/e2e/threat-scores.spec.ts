import { test, expect } from "@playwright/test";
import { loginAsAdmin } from "./helpers/auth";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("Threat scores page", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("loads leaderboard after login", async ({ page }) => {
    await loginAsAdmin(page);

    await page.goto("/threat-scores");
    await expect(page.getByRole("heading", { name: /threat scores/i })).toBeVisible();
    await expect(page.getByText(/threat score leaderboard/i)).toBeVisible();
  });
});
