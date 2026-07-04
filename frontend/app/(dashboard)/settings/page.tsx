"use client";

import { memo, useMemo, useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils/cn";
import { NotificationSettingsPanel } from "@/components/NotificationSettingsPanel";
import { QueryError } from "@/components/ui/QueryError";

type Category = "appearance" | "notifications" | "system";

const categories: { id: Category; label: string }[] = [
  { id: "appearance", label: "Appearance" },
  { id: "notifications", label: "Notifications" },
  { id: "system", label: "System" },
];

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
          <select
            className="input-siem w-auto min-w-[140px] text-body py-1.5"
            value={theme === "dark" ? "Dark" : "Light"}
            onChange={(e) => setTheme(e.target.value === "Dark" ? "dark" : "light")}
            aria-label="Theme"
          >
            <option value="Dark">Dark</option>
            <option value="Light">Light</option>
          </select>
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

  const { data: publicConfig, isError, refetch } = useQuery({
    queryKey: ["settings", "public"],
    queryFn: () => api<{ environment: string; retention_days: number; allow_registration: boolean }>("/api/v1/settings/public"),
    staleTime: 300_000,
  });

  const filtered = useMemo(() => {
    if (!search.trim()) return categories;
    const q = search.toLowerCase();
    return categories.filter((c) => c.label.toLowerCase().includes(q));
  }, [search]);

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader title="Settings" subtitle="Appearance, notifications, and system configuration" />
      <div className="relative max-w-sm">
        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
        <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search settings…" className="input-siem pl-9" />
      </div>
      <div className="flex flex-col lg:flex-row gap-6">
        <nav className="lg:w-48 shrink-0 flex lg:flex-col gap-1" role="tablist">
          {filtered.map((cat) => (
            <button
              key={cat.id}
              role="tab"
              aria-selected={active === cat.id}
              onClick={() => setActive(cat.id)}
              className={cn(
                "px-3 py-2 rounded-md text-body font-medium text-left whitespace-nowrap transition-colors",
                active === cat.id ? "bg-[var(--sidebar-active)] text-accent" : "text-muted hover:text-foreground hover:bg-[var(--sidebar-hover)]",
              )}
            >
              {cat.label}
            </button>
          ))}
        </nav>
        <div className="flex-1 min-w-0">
          {active === "appearance" && <AppearanceSettings />}
          {active === "notifications" && <NotificationSettingsPanel />}
          {active === "system" && (isError ? <QueryError onRetry={() => refetch()} /> : <SystemSettings publicConfig={publicConfig} />)}
        </div>
      </div>
    </div>
  );
}
