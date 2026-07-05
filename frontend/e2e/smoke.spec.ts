import { test, expect } from "@playwright/test";

test.describe("SecuriSphere smoke", () => {
  test("login page loads", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /sign in|login/i })).toBeVisible();
  });

  test("register page loads", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("button", { name: /register|create/i })).toBeVisible();
  });
});
