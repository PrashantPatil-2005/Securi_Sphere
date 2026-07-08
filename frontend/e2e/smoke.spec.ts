import { test, expect } from "@playwright/test";
import { dismissBlockingOverlays, loginAsAdmin } from "./helpers/auth";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("Securi smoke", () => {
  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /sign in|login/i })).toBeVisible();
  });

  test("register page loads", async ({ page }) => {
    await page.goto("/register");
    const createAccount = page.getByRole("button", { name: /create account/i });
    const registrationClosed = page.getByRole("heading", { name: /registration closed/i });
    const registrationDisabled = page.getByText(/registration is disabled|invite-only|self-service sign-up is disabled/i);
    await expect(createAccount.or(registrationClosed).or(registrationDisabled)).toBeVisible({
      timeout: 15_000,
    });
  });

  test.describe("authenticated", () => {
    test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

    test("critical pages load after login", async ({ page }) => {
      await loginAsAdmin(page);
      for (const path of ["/rules", "/alerts", "/simulation"]) {
        await page.goto(path);
        await dismissBlockingOverlays(page);
        await expect(page.locator("h1").first()).toBeVisible({ timeout: 15_000 });
      }
    });
  });
});
