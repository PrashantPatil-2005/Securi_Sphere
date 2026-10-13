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

  const passwords = [
    process.env.E2E_ADMIN_PASSWORD,
    process.env.DEV_USER_PASSWORD,
    "testpass123",
    "newpass456",
    "Admin1234!",
    "Securi2026!",
  ].filter((p): p is string => Boolean(p));
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

  // Header button opens the Add Host dialog.
  await page.getByRole("button", { name: "Add Host", exact: true }).first().click();

  const addDialog = page.getByRole("dialog", { name: "Add Host" });
  await expect(addDialog).toBeVisible({ timeout: 15_000 });
  await addDialog.getByPlaceholder("e.g. server-prod-03").fill(hostName);
  await addDialog.getByRole("button", { name: "Add Host", exact: true }).click();

  // Success opens an Enrollment Token dialog that must be dismissed.
  const tokenDialog = page.getByRole("dialog", { name: /Enrollment Token/i });
  await expect(tokenDialog).toBeVisible({ timeout: 15_000 });
  await tokenDialog.getByRole("button", { name: "Done" }).click();

  await expect(page.getByText(hostName).first()).toBeVisible({ timeout: 15_000 });
}
