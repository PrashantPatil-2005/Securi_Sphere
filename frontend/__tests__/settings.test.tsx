import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/lib/theme/ThemeProvider", () => ({
  useTheme: () => ({
    theme: "dark",
    setTheme: vi.fn(),
    reducedMotion: false,
    setReducedMotion: vi.fn(),
  }),
}));

vi.mock("@/lib/hooks/useUser", () => ({
  useUser: () => ({
    data: { role: { name: "admin" } },
  }),
}));

vi.mock("@/components/NotificationSettingsPanel", () => ({
  NotificationSettingsPanel: () => <div data-testid="notification-settings">Notification Settings</div>,
}));

vi.mock("@/components/settings/NotificationRulesPanel", () => ({
  NotificationRulesPanel: () => <div data-testid="notification-rules">Notification Rules</div>,
}));

vi.mock("@/components/settings/TeamManagementPanel", () => ({
  TeamManagementPanel: () => <div data-testid="team-management">Team Management</div>,
}));

vi.mock("@/components/settings/PlaybooksPanel", () => ({
  PlaybooksPanel: () => <div data-testid="playbooks">Playbooks</div>,
}));

import SettingsPage from "@/app/(dashboard)/settings/page";

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe("SettingsPage", () => {
  it("renders page title", () => {
    wrap(<SettingsPage />);
    expect(screen.getByText("Settings")).toBeTruthy();
  });

  it("renders subtitle", () => {
    wrap(<SettingsPage />);
    expect(
      screen.getByText(
        "Appearance, notifications, system configuration, and team management",
      ),
    ).toBeTruthy();
  });

  it("renders Appearance tab by default", () => {
    wrap(<SettingsPage />);
    expect(screen.getByText("Theme")).toBeTruthy();
    expect(screen.getByText("Reduced motion")).toBeTruthy();
  });

  it("renders theme select with Dark/Light options", () => {
    wrap(<SettingsPage />);
    const select = screen.getByLabelText("Theme");
    expect(select).toBeTruthy();
    expect(screen.getByText("Dark")).toBeTruthy();
    expect(screen.getByText("Light")).toBeTruthy();
  });

  it("renders Notifications tab", () => {
    wrap(<SettingsPage />);
    expect(screen.getByText("Notifications")).toBeTruthy();
  });

  it("renders Playbooks tab for admin", () => {
    wrap(<SettingsPage />);
    expect(screen.getByText("Playbooks")).toBeTruthy();
  });

  it("renders Team tab for admin", () => {
    wrap(<SettingsPage />);
    expect(screen.getByText("Team")).toBeTruthy();
  });

  it("renders System tab", () => {
    wrap(<SettingsPage />);
    expect(screen.getByText("System")).toBeTruthy();
  });

  it("renders reduced motion toggle", () => {
    wrap(<SettingsPage />);
    const toggle = screen.getByLabelText("Reduced motion");
    expect(toggle).toBeTruthy();
    expect(toggle.getAttribute("type")).toBe("checkbox");
  });
});
