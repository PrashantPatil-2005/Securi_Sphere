"use client";

import { memo, useMemo, useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils/cn";
import { NotificationSettingsPanel } from "@/components/NotificationSettingsPanel";

type Category = "appearance" | "notifications" | "system";

const categories: { id: Category; label: string }[] = [
  { id: "appearance", label: "Appearance" },
  { id: "notifications", label: "Notifications" },
  { id: "system", label: "System" },
];

type Field = {
  label: string;
  desc: string;
  type: "toggle" | "select" | "readonly";
  options?: string[];
  default?: boolean | string;
  comingSoon?: boolean;
  wired?: boolean;
};

const settingsContent: Record<Category, { title: string; fields: Field[] }> = {
  appearance: {
    title: "Appearance",
    fields: [
      { label: "Theme", desc: "Choose light or dark mode", type: "select", options: ["Dark", "Light"], default: "Dark", wired: true },
      { label: "Reduced motion", desc: "Minimize animations", type: "toggle", default: false, comingSoon: true },
      { label: "High contrast", desc: "Increase color contrast", type: "toggle", default: false, comingSoon: true },
    ],
  },
  notifications: {
    title: "Notification Settings",
    fields: [
      { label: "Email alerts", desc: "Send critical alerts via email", type: "toggle", default: false, wired: true },
      { label: "Slack integration", desc: "Forward alerts to Slack", type: "toggle", default: false, wired: true },
      { label: "Telegram", desc: "Forward alerts to Telegram", type: "toggle", default: false, wired: true },
      { label: "Alert threshold", desc: "Minimum severity for notifications", type: "select", options: ["Critical", "High", "Medium", "Low"], default: "High", comingSoon: true },
    ],
  },
  system: {
    title: "System (read-only)",
    fields: [
      { label: "Environment", desc: "Deployment environment", type: "readonly" },
      { label: "Data retention", desc: "Days to retain events and metrics", type: "readonly" },
      { label: "Registration", desc: "Public user registration", type: "readonly" },
    ],
  },
};

const SettingsForm = memo(function SettingsForm({
  category,
  publicConfig,
}: {
  category: Category;
  publicConfig?: { environment: string; retention_days: number; allow_registration: boolean };
}) {
  const content = settingsContent[category];
  const { theme, setTheme } = useTheme();
  const { toast } = useToast();

  return (
    <Panel title={content.title}>
      <div className="space-y-4">
        {content.fields.map((field) => (
          <div key={field.label} className="flex items-start justify-between gap-4 py-3 border-b border-border-subtle/50 last:border-0">
            <div className="flex-1 min-w-0">
              <p className="text-body font-medium text-foreground flex items-center gap-2">
                {field.label}
                {field.comingSoon && (
                  <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted/20 text-muted">Coming soon</span>
                )}
              </p>
              <p className="text-caption normal-case text-muted mt-0.5">{field.desc}</p>
            </div>
            {field.comingSoon && field.type === "toggle" && (
              <input type="checkbox" disabled className="opacity-40" />
            )}
            {!field.comingSoon && field.type === "toggle" && category !== "system" && (
              <label className="relative inline-flex items-center cursor-pointer shrink-0">
                <input type="checkbox" defaultChecked={field.default as boolean} className="sr-only peer" disabled={!field.wired} />
                <div className="w-9 h-5 bg-border rounded-full peer-checked:bg-accent transition-colors opacity-80" />
              </label>
            )}
            {field.type === "select" && field.label === "Theme" && (
              <select
                className="input-siem w-auto min-w-[140px] text-body py-1.5"
                value={theme === "dark" ? "Dark" : "Light"}
                onChange={(e) => setTheme(e.target.value === "Dark" ? "dark" : "light")}
              >
                <option value="Dark">Dark</option>
                <option value="Light">Light</option>
              </select>
            )}
            {field.type === "readonly" && publicConfig && (
              <span className="text-body text-muted">
                {field.label === "Environment" && publicConfig.environment}
                {field.label === "Data retention" && `${publicConfig.retention_days} days`}
                {field.label === "Registration" && (publicConfig.allow_registration ? "Enabled" : "Disabled")}
              </span>
            )}
          </div>
        ))}
        {category === "notifications" && (
          <p className="text-caption normal-case text-muted">Configure delivery channels in Profile → Notification preferences (API wired in Notifications tab).</p>
        )}
        {category !== "system" && (
          <div className="pt-2">
            <Button onClick={() => toast("success", "Settings saved", category === "appearance" ? "Theme updated" : "Preferences saved")}>
              Save changes
            </Button>
          </div>
        )}
      </div>
    </Panel>
  );
});

export default function SettingsPage() {
  const [active, setActive] = useState<Category>("appearance");
  const [search, setSearch] = useState("");

  const { data: publicConfig } = useQuery({
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
      <PageHeader title="Settings" subtitle="Working preferences only — unimplemented options are marked Coming soon" />
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
          {active === "notifications" ? <NotificationSettingsPanel /> : <SettingsForm category={active} publicConfig={publicConfig} />}
        </div>
      </div>
    </div>
  );
}
