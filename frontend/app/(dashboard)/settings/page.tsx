"use client";

import { memo, useMemo, useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { api } from "@/lib/api";
import { NotificationSettingsPanel } from "@/components/NotificationSettingsPanel";
import { NotificationRulesPanel } from "@/components/settings/NotificationRulesPanel";
import { TeamManagementPanel } from "@/components/settings/TeamManagementPanel";
import { PlaybooksPanel } from "@/components/settings/PlaybooksPanel";
import { QueryError } from "@/components/ui/QueryError";
import { Tabs, TabPanel } from "@/components/ui/Tabs";
import { useUser } from "@/lib/hooks/useUser";

type Category = "appearance" | "notifications" | "system" | "automation" | "team";

const AppearanceSettings = memo(function AppearanceSettings() {
  const { theme, setTheme, reducedMotion, setReducedMotion } = useTheme();

  return (
    <Panel title="Appearance">
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4 py-3 border-b border-border-subtle/50">
          <div className="flex-1 min-w-0">
            <p className="text-body font-medium text-foreground">Theme</p>
            <p className="text-caption normal-case text-muted mt-0.5">Choose light or dark mode. Saved automatically.</p>
          </div>
          <Select
            className="w-auto min-w-[140px]"
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
            <p className="text-body font-medium text-foreground">Reduced motion</p>
            <p className="text-caption normal-case text-muted mt-0.5">Minimize animations across the dashboard.</p>
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
    </Panel>
  );
});

const SystemSettings = memo(function SystemSettings({
  publicConfig,
}: {
  publicConfig?: { environment: string; retention_days: number; allow_registration: boolean };
}) {
  const rows = [
    { label: "Environment", value: publicConfig?.environment ?? "—" },
    { label: "Data retention", value: publicConfig ? `${publicConfig.retention_days} days` : "—" },
    {
      label: "Registration",
      value: publicConfig ? (publicConfig.allow_registration ? "Enabled" : "Disabled") : "—",
    },
  ];

  return (
    <Panel title="System">
      <p className="text-caption normal-case text-muted mb-4">Deployment configuration (read-only).</p>
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.label} className="flex items-start justify-between gap-4 py-2 border-b border-border-subtle/50 last:border-0">
            <span className="text-body font-medium text-foreground">{row.label}</span>
            <span className="text-body text-muted capitalize">{row.value}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
});

export default function SettingsPage() {
  const [active, setActive] = useState<Category>("appearance");
  const [search, setSearch] = useState("");
  const { data: user } = useUser();
  const isAdmin = user?.role?.name === "admin";
  const isAnalyst = user?.role?.name === "analyst" || isAdmin;

  const categories = useMemo(() => {
    const base: { id: Category; label: string }[] = [
      { id: "appearance", label: "Appearance" },
      { id: "notifications", label: "Notifications" },
      { id: "system", label: "System" },
    ];
    if (isAnalyst) base.push({ id: "automation", label: "Playbooks" });
    if (isAdmin) base.push({ id: "team", label: "Team" });
    return base;
  }, [isAdmin, isAnalyst]);

  const tabItems = useMemo(
    () => categories.map((c) => ({ id: c.id, label: c.label, panelId: `settings-panel-${c.id}` })),
    [categories],
  );

  const { data: publicConfig, isError, refetch } = useQuery({
    queryKey: ["settings", "public"],
    queryFn: () => api<{ environment: string; retention_days: number; allow_registration: boolean }>("/api/v1/settings/public"),
    staleTime: 300_000,
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return categories;
    const q = search.toLowerCase();
    return categories.filter((c) => c.label.toLowerCase().includes(q));
  }, [search, categories]);

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader title="Settings" subtitle="Appearance, notifications, and system configuration" />
      <div className="relative max-w-sm">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none z-10" aria-hidden />
        <Input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search settings…"
          className="pl-9"
          aria-label="Search settings"
        />
      </div>
      <div className="flex flex-col lg:flex-row gap-6">
        <Tabs
          tabs={filtered.length ? tabItems.filter((t) => filtered.some((c) => c.id === t.id)) : tabItems}
          active={active}
          onChange={setActive}
          variant="sidebar"
          ariaLabel="Settings categories"
          className="lg:w-48 shrink-0"
        />
        <TabPanel id={`settings-panel-${active}`} labelledBy={`tab-${active}`} className="flex-1 min-w-0">
          {active === "appearance" && <AppearanceSettings />}
          {active === "notifications" && (
            <div className="space-y-6">
              <NotificationSettingsPanel />
              <NotificationRulesPanel />
            </div>
          )}
          {active === "system" && (isError ? <QueryError onRetry={() => refetch()} /> : <SystemSettings publicConfig={publicConfig} />)}
          {active === "automation" && isAnalyst && <PlaybooksPanel isAdmin={isAdmin} />}
          {active === "team" && isAdmin && <TeamManagementPanel />}
        </TabPanel>
      </div>
    </div>
  );
}
