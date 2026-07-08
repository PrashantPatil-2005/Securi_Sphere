"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  FlaskConical,
  Bell,
  LayoutDashboard,
  Server,
  ShieldAlert,
  Wrench,
  BarChart3,
  Gauge,
  Activity,
  Inbox,
  FolderSearch,
  AlertTriangle,
  Target,
  Clock,
  Network,
  Shield,
  BookMarked,
  FileText,
  ScrollText,
  Settings,
  User,
} from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { canAccessRoute, useUser } from "@/lib/hooks/useUser";
import { cn } from "@/lib/utils/cn";

interface CommandItem {
  id: string;
  label: string;
  path: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
  keywords?: string[];
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);
  const inputId = useId();
  const listboxId = useId();
  const router = useRouter();
  const { data: user } = useUser();
  const role = user?.role?.name;

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
  }, []);

  const navigate = useCallback(
    (path: string) => {
      router.push(path);
      close();
    },
    [router, close],
  );

  const items: CommandItem[] = useMemo(() => {
    const all: CommandItem[] = [
      { id: "dash", label: "Go to Dashboard", path: "/", icon: LayoutDashboard, action: () => navigate("/"), keywords: ["home", "overview"] },
      { id: "analytics", label: "Go to Analytics", path: "/analytics", icon: BarChart3, action: () => navigate("/analytics"), keywords: ["siem", "ueba", "charts"] },
      { id: "threat-scores", label: "Threat score leaderboard", path: "/threat-scores", icon: ShieldAlert, action: () => navigate("/threat-scores"), keywords: ["risk", "ranking", "hosts"] },
      { id: "metrics", label: "Go to Metrics", path: "/metrics", icon: Gauge, action: () => navigate("/metrics"), keywords: ["host metrics"] },
      { id: "hosts", label: "Go to Hosts", path: "/hosts", icon: Server, action: () => navigate("/hosts"), keywords: ["add host", "enroll"] },
      { id: "maintenance", label: "Maintenance windows", path: "/maintenance", icon: Wrench, action: () => navigate("/maintenance"), keywords: ["downtime", "patching", "suppress"] },
      { id: "events", label: "Go to Events", path: "/events", icon: Activity, action: () => navigate("/events"), keywords: ["logs", "ingest"] },
      { id: "alerts", label: "Go to Alerts", path: "/alerts", icon: Bell, action: () => navigate("/alerts"), keywords: ["triage", "open", "detection"] },
      { id: "notifications", label: "Go to Notifications", path: "/notifications", icon: Inbox, action: () => navigate("/notifications"), keywords: ["inbox", "messages"] },
      { id: "offenses", label: "Go to Offenses", path: "/offenses", icon: ShieldAlert, action: () => navigate("/offenses"), keywords: ["correlation", "grouped"] },
      { id: "workspace", label: "Open Case Workspace", path: "/investigation", icon: FolderSearch, action: () => navigate("/investigation"), keywords: ["investigate", "case", "triage", "workspace"] },
      { id: "incidents", label: "Go to Incidents", path: "/incidents", icon: AlertTriangle, action: () => navigate("/incidents"), keywords: ["investigation", "case management"] },
      { id: "mitre", label: "Go to MITRE ATT&CK", path: "/mitre", icon: Target, action: () => navigate("/mitre"), keywords: ["attack", "techniques", "heatmap"] },
      { id: "timeline", label: "Go to Timeline", path: "/timeline", icon: Clock, action: () => navigate("/timeline"), keywords: ["attack chain", "replay"] },
      { id: "network", label: "Go to Network", path: "/network", icon: Network, action: () => navigate("/network"), keywords: ["topology", "graph"] },
      { id: "search", label: "SIEM Search", path: "/search", icon: Search, action: () => navigate("/search"), keywords: ["query", "siem", "saved search"] },
      { id: "sim", label: "Open Attack Lab", path: "/simulation", icon: FlaskConical, action: () => navigate("/simulation"), keywords: ["attack", "lab", "demo", "simulation"] },
      { id: "rules", label: "Go to Detection Rules", path: "/rules", icon: Shield, action: () => navigate("/rules"), keywords: ["correlation", "detection"] },
      { id: "intel", label: "Go to Threat Intel", path: "/intel", icon: BookMarked, action: () => navigate("/intel"), keywords: ["ioc", "reference sets", "building blocks"] },
      { id: "reports", label: "Go to Reports", path: "/reports", icon: FileText, action: () => navigate("/reports"), keywords: ["compliance", "executive", "pdf"] },
      { id: "audit", label: "Go to Audit Log", path: "/audit", icon: ScrollText, action: () => navigate("/audit"), keywords: ["admin", "activity"] },
      { id: "system", label: "Go to System Health", path: "/system", icon: Activity, action: () => navigate("/system"), keywords: ["health", "pipeline", "status"] },
      { id: "system-ops", label: "Open ops console", path: "/system", icon: Activity, action: () => navigate("/system"), keywords: ["admin", "circuits", "replica", "mv refresh", "ops"] },
      { id: "rules-tuning", label: "Rule tuning insights", path: "/rules", icon: Shield, action: () => navigate("/rules"), keywords: ["false positive", "feedback", "tuning"] },
      { id: "settings", label: "Go to Settings", path: "/settings", icon: Settings, action: () => navigate("/settings"), keywords: ["team", "notifications", "playbooks"] },
      { id: "profile", label: "Go to Profile", path: "/profile", icon: User, action: () => navigate("/profile"), keywords: ["account", "password"] },
    ];
    return all.filter((item) => canAccessRoute(role, item.path));
  }, [navigate, role]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.keywords?.some((k) => k.includes(q) || q.includes(k)),
    );
  }, [items, query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    if (filtered.length === 0) return;
    setActiveIndex((i) => Math.min(i, filtered.length - 1));
  }, [filtered.length]);

  const activeId = filtered[activeIndex] ? `cmd-${filtered[activeIndex].id}` : undefined;

  useEffect(() => {
    if (!activeId || !listRef.current) return;
    const activeEl = listRef.current.querySelector(`#${CSS.escape(activeId)}`);
    activeEl?.scrollIntoView({ block: "nearest" });
  }, [activeId]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
        setQuery("");
      }
      if (!open) return;
      if (filtered.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      }
      if (e.key === "Home") {
        e.preventDefault();
        setActiveIndex(0);
      }
      if (e.key === "End") {
        e.preventDefault();
        setActiveIndex(filtered.length - 1);
      }
      if (e.key === "Enter" && filtered[activeIndex]) {
        e.preventDefault();
        filtered[activeIndex].action();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, filtered, activeIndex]);

  return (
    <Dialog
      open={open}
      onClose={close}
      title="Command palette"
      showHeader={false}
      align="top"
      zIndex={100}
      size="md"
      className="max-w-lg rounded-xl border border-border bg-card p-0 max-h-none overflow-hidden shadow-2xl"
    >
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border-subtle">
        <Search className="w-4 h-4 text-muted shrink-0" aria-hidden />
        <input
          id={inputId}
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search pages and actions…"
          className="flex-1 bg-transparent outline-none text-sm"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded="true"
          aria-controls={listboxId}
          aria-activedescendant={activeId}
          aria-label="Search commands"
        />
        <kbd className="text-[10px] text-muted px-1.5 py-0.5 rounded border border-border-subtle">Esc</kbd>
      </div>
      <ul
        ref={listRef}
        id={listboxId}
        role="listbox"
        aria-label="Commands"
        className="max-h-72 overflow-y-auto py-2"
      >
        {filtered.length === 0 && (
          <li className="px-4 py-3 text-sm text-muted" role="presentation">No matches</li>
        )}
        {filtered.map((item, i) => {
          const Icon = item.icon;
          return (
            <li
              key={item.id}
              id={`cmd-${item.id}`}
              role="option"
              aria-selected={i === activeIndex}
              onMouseMove={() => setActiveIndex(i)}
              onClick={() => item.action()}
              className={cn(
                "flex items-center gap-3 px-4 py-2.5 text-sm cursor-pointer hover:bg-[var(--sidebar-hover)]",
                i === activeIndex && "bg-[var(--sidebar-hover)]",
              )}
            >
              <Icon className="w-4 h-4 text-muted shrink-0" aria-hidden />
              <span>{item.label}</span>
            </li>
          );
        })}
      </ul>
      <div className="px-4 py-2 border-t border-border-subtle text-[10px] text-muted flex gap-3">
        <span>↑↓ navigate</span>
        <span>↵ select</span>
        <span>Ctrl+K toggle</span>
      </div>
    </Dialog>
  );
}
