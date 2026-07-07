import { expect, type Page } from "@playwright/test";

/** Sign in through the login form (works with split frontend/API hosts). */
export async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("admin@test.local");
  await page.locator("#password").fill("testpass123");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL("/", { timeout: 60_000 });
}

export async function addHost(page: Page, hostName: string) {
  await page.goto("/hosts");
  await page.getByPlaceholder("New host name").fill(hostName);
  await page.getByRole("button", { name: "Add host" }).click();
  await expect(page.getByText(hostName).first()).toBeVisible({ timeout: 15_000 });
}
