"use client";

import { Suspense, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/ui/Panel";
import { Card, CardHeader } from "@/components/design-system/Card";
import { Select } from "@/components/design-system/Select";
import { QueryError } from "@/components/ui/QueryError";
import { LoadingState } from "@/components/design-system/LoadingState";
import { api } from "@/lib/api";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { useUser } from "@/lib/hooks/useUser";
import { NotificationSettingsPanel } from "@/components/NotificationSettingsPanel";
import { NotificationRulesPanel } from "@/components/settings/NotificationRulesPanel";
import { TeamManagementPanel } from "@/components/settings/TeamManagementPanel";
import { PlaybooksPanel } from "@/components/settings/PlaybooksPanel";

type Tab = "appearance" | "notifications" | "playbooks" | "team" | "system";

function AppearanceTab() {
  const { theme, setTheme, reducedMotion, setReducedMotion } = useTheme();

  return (
    <Card>
      <CardHeader title="Appearance" subtitle="Theme and visual preferences" />
      <div className="p-4 space-y-4">
        <div className="flex items-start justify-between gap-4 py-3 border-b border-border-subtle">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">Theme</p>
            <p className="text-xs text-muted mt-0.5">Choose light or dark mode. Saved automatically.</p>
          </div>
          <Select
            className="!w-auto min-w-[120px]"
            value={theme === "dark" ? "Dark" : "Light"}
            onChange={(e) => setTheme(e.target.value === "Dark" ? "dark" : "light")}
            aria-label="Theme"
          >
            <option value="Dark">Dark</option>
            <option value="Light">Light</option>
          </Select>
        </div>
        <div className="flex items-start justify-between gap-4 py-3">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">Reduced motion</p>
            <p className="text-xs text-muted mt-0.5">Minimize animations across the dashboard.</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer shrink-0">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={reducedMotion}
              onChange={(e) => setReducedMotion(e.target.checked)}
              aria-label="Reduced motion"
            />
            <div className="w-9 h-5 bg-border rounded-full peer-checked:bg-accent transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-accent" />
          </label>
        </div>
      </div>
    </Card>
  );
}

function SystemTab() {
  const { data: config, isLoading, isError, refetch } = useQuery({
    queryKey: ["settings", "public"],
    queryFn: () =>
      api<{
        environment: string;
        retention_days: number;
        allow_registration: boolean;
        oidc_enabled: boolean;
        search_backend: string;
        demo_mode: boolean;
      }>("/api/v1/settings/public"),
    staleTime: 300_000,
  });

  if (isError) return <QueryError onRetry={() => refetch()} />;
  if (isLoading) return <LoadingState rows={3} />;

  const rows = [
    { label: "Environment", value: config?.environment ?? "—" },
    { label: "Data retention", value: config ? `${config.retention_days} days` : "—" },
    { label: "Registration", value: config ? (config.allow_registration ? "Enabled" : "Disabled") : "—" },
    { label: "OIDC/SSO", value: config ? (config.oidc_enabled ? "Enabled" : "Disabled") : "—" },
    { label: "Search backend", value: config?.search_backend ?? "—" },
    { label: "Demo mode", value: config ? (config.demo_mode ? "Enabled" : "Disabled") : "—" },
  ];

  return (
    <Card>
      <CardHeader title="System Information" subtitle="Deployment configuration (read-only)" />
      <div className="p-4 space-y-3">
        {rows.map((row) => (
          <div key={row.label} className="flex items-start justify-between gap-4 py-2 border-b border-border-subtle last:border-0">
            <span className="text-sm font-medium">{row.label}</span>
            <span className="text-sm text-muted capitalize">{row.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function NotificationsTab() {
  return (
    <div className="space-y-6">
      <NotificationSettingsPanel />
      <NotificationRulesPanel />
    </div>
  );
}

function SettingsPageContent() {
  const { data: user } = useUser();
  const isAdmin = user?.role?.name === "admin";
  const isAnalyst = user?.role?.name === "analyst" || isAdmin;

  const [activeTab, setActiveTab] = useState<Tab>("appearance");

  const tabs = useMemo(() => {
    const items: { id: Tab; label: string; adminOnly?: boolean; analystOrAbove?: boolean }[] = [
      { id: "appearance", label: "Appearance" },
      { id: "notifications", label: "Notifications" },
      { id: "playbooks", label: "Playbooks", analystOrAbove: true },
      { id: "team", label: "Team", adminOnly: true },
      { id: "system", label: "System" },
    ];
    return items.filter((t) => {
      if (t.adminOnly && !isAdmin) return false;
      if (t.analystOrAbove && !isAnalyst) return false;
      return true;
    });
  }, [isAdmin, isAnalyst]);

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Settings"
        subtitle="Appearance, notifications, system configuration, and team management"
      />

      {/* Tab navigation */}
      <div className="flex gap-1 border-b border-border-subtle" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div role="tabpanel" id={`panel-${activeTab}`}>
        {activeTab === "appearance" && <AppearanceTab />}
        {activeTab === "notifications" && <NotificationsTab />}
        {activeTab === "playbooks" && isAnalyst && <PlaybooksPanel isAdmin={isAdmin} />}
        {activeTab === "team" && isAdmin && <TeamManagementPanel />}
        {activeTab === "system" && <SystemTab />}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<LoadingState rows={4} />}>
      <SettingsPageContent />
    </Suspense>
  );
}
