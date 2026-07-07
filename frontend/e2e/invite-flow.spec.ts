import { test, expect } from "@playwright/test";

const fullStack = !!process.env.E2E_FULL_STACK;

test.describe("Invite acceptance flow", () => {
  test.skip(!fullStack, "Set E2E_FULL_STACK=1 with backend + Postgres running");

  test("admin invites user → accept invite → dashboard", async ({ page, request }) => {
    const stamp = Date.now();
    const email = `invited-e2e-${stamp}@test.local`;
    const password = "InvitePass123!";

    const loginRes = await request.post("http://localhost:8000/api/v1/auth/login", {
      data: { email: "admin@test.local", password: "testpass123" },
    });
    expect(loginRes.ok()).toBeTruthy();

    const inviteRes = await request.post("http://localhost:8000/api/v1/users/invites", {
      data: { email, role: "viewer", full_name: "E2E Invited" },
    });
    expect(inviteRes.ok()).toBeTruthy();
    const invite = await inviteRes.json();
    expect(invite.invite_url).toBeTruthy();
    const token = new URL(invite.invite_url).searchParams.get("token");
    expect(token).toBeTruthy();

    await page.goto(`/accept-invite?token=${token}`);
    await expect(page.getByRole("heading", { name: "Accept invitation" })).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();

    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL("/", { timeout: 15_000 });
    await expect(page.getByText(/getting started|dashboard/i).first()).toBeVisible({ timeout: 10_000 });
  });
});
