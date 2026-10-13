import { test, expect } from "@playwright/test";
import { addHost, dismissBlockingOverlays, loginAsAdmin } from "./helpers/auth";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("SOC lab flow", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("golden path: login → simulation → alerts → offenses → case workspace → timeline", async ({ page }) => {
    // Streamed attacks replay over 6-18s of wall clock plus per-event detection.
    test.setTimeout(240_000);
    await loginAsAdmin(page);

    // The simulation page auto-selects hosts[0] and disables "Run simulation"
    // when the host list is empty, so the golden path must create its own
    // target rather than assuming seeded data is present.
    await addHost(page, `lab-flow-${Date.now()}`);

    await page.goto("/simulation");
    await dismissBlockingOverlays(page);
    await expect(page.getByRole("heading", { name: "Attack Simulation Lab" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Presets" })).toBeVisible();
    await page.getByRole("button", { name: /run simulation/i }).click();
    await expect(page.getByRole("heading", { name: /simulation complete/i })).toBeVisible({ timeout: 90_000 });
    await expect(page.locator("p", { hasText: /^Guided investigation$/ })).toBeVisible();

    await page.getByRole("link", { name: /triage alerts/i }).first().click();
    await expect(page).toHaveURL(/\/alerts/);
    await expect(page.locator(".data-table-row").first()).toBeVisible({ timeout: 30_000 });

    await page.goto("/offenses");
    await expect(page.getByRole("heading", { name: "Offenses" })).toBeVisible();
    await page.getByRole("button", { name: /events/i }).first().click({ timeout: 30_000 });

    // The sidebar also has a "Case Workspace" nav link, so scope to main.
    const caseWorkspaceLink = page
      .getByRole("main")
      .getByRole("link", { name: "Case Workspace" });
    await expect(caseWorkspaceLink).toBeVisible();
    await caseWorkspaceLink.click();
    await expect(page).toHaveURL(/\/investigation\?offense=/);
    await expect(page.getByRole("heading", { name: "Case Workspace" })).toBeVisible();
    await expect(page.getByText("Primary alert")).toBeVisible({ timeout: 15_000 });

    await page.goto("/timeline");
    await expect(
      page.getByRole("heading", { name: "Attack Timelines", level: 1 }),
    ).toBeVisible({ timeout: 15_000 });

    await page.goto("/simulation");
    await page.getByRole("tab", { name: "Custom" }).click();
    // The custom builder mounts on tab switch; wait for its own content so the
    // click lands on a fully hydrated "Run custom simulation" button.
    await expect(page.getByRole("heading", { name: "Event steps" })).toBeVisible();
    await page.getByRole("button", { name: /run custom simulation/i }).click();
    await expect(page.getByRole("heading", { name: /simulation complete/i })).toBeVisible({
      timeout: 90_000,
    });

    await page.getByRole("tab", { name: "History" }).click();
    await expect(page.getByText("Run history")).toBeVisible();
    await expect(page.getByText("Custom attack chain").or(page.getByText(/custom/i)).first()).toBeVisible({
      timeout: 10_000,
    });
  });
});
