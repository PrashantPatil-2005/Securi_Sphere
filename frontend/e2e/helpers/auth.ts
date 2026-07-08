import { expect, type Page } from "@playwright/test";

/** Close onboarding/demo overlays that block page interactions. */
export async function dismissBlockingOverlays(page: Page) {
  await page.evaluate(() => {
    localStorage.setItem("securi_onboarding_wizard_done", "1");
  });

  const skipTour = page.getByRole("button", { name: /skip tour/i });
  if (await skipTour.isVisible().catch(() => false)) {
    await skipTour.click();
  }

  const closeDialog = page.getByRole("button", { name: /^close$/i });
  if (await closeDialog.isVisible().catch(() => false)) {
    await closeDialog.click();
  }

  await expect(page.getByRole("dialog", { name: /welcome to securi/i }))
    .toBeHidden({ timeout: 10_000 })
    .catch(() => {});

  const dismissDemo = page.getByRole("button", { name: /dismiss demo notice/i });
  if (await dismissDemo.isVisible().catch(() => false)) {
    await dismissDemo.click();
  }
}

/** Sign in through the API proxy (more reliable than form clicks in E2E). */
export async function loginAsAdmin(page: Page) {
  await page.goto("/login");
  await expect(page.getByLabel("Email address")).toBeVisible({ timeout: 30_000 });

  const passwords = ["testpass123", "newpass456"];
  let loggedIn = false;

  for (const password of passwords) {
    for (let attempt = 0; attempt < 3; attempt++) {
      const status = await page.evaluate(async (pwd) => {
        const res = await fetch("/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ email: "admin@test.local", password: pwd }),
        });
        return res.status;
      }, password);

      if (status === 200) {
        loggedIn = true;
        break;
      }
      if (status >= 500) {
        await page.waitForTimeout(1500);
        continue;
      }
      break;
    }
    if (loggedIn) break;
  }

  expect(loggedIn, "Admin login failed for known test credentials").toBeTruthy();

  await page.evaluate(async () => {
    const me = await fetch("/api/v1/auth/me", { credentials: "include" });
    if (!me.ok) throw new Error(`auth/me failed: ${me.status}`);
    document.cookie = "ss_auth=1; path=/; max-age=604800; SameSite=Lax";
  });

  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible({
    timeout: 60_000,
  });
  await dismissBlockingOverlays(page);
}

export async function addHost(page: Page, hostName: string) {
  await page.goto("/hosts");
  await dismissBlockingOverlays(page);
  await expect(page.getByPlaceholder("New host name")).toBeVisible({ timeout: 15_000 });
  await page.getByPlaceholder("New host name").fill(hostName);
  await page.getByRole("button", { name: "Add host" }).click();
  await expect(page.getByText(hostName).first()).toBeVisible({ timeout: 15_000 });
}
