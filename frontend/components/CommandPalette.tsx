"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, FlaskConical, Bell, LayoutDashboard, Server, ShieldAlert, Wrench } from "lucide-react";
import { useBodyScrollLock } from "@/lib/hooks/useBodyScrollLock";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { cn } from "@/lib/utils/cn";

interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  action: () => void;
  keywords?: string[];
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const titleId = useId();
  const inputId = useId();
  const listboxId = useId();
  const router = useRouter();

  useBodyScrollLock(open);
  useFocusTrap(panelRef, open);

  const navigate = useCallback(
    (path: string) => {
      router.push(path);
      setOpen(false);
      setQuery("");
    },
    [router],
  );

  const items: CommandItem[] = useMemo(
    () => [
      { id: "dash", label: "Go to Dashboard", icon: LayoutDashboard, action: () => navigate("/") },
      { id: "hosts", label: "Go to Hosts", icon: Server, action: () => navigate("/hosts"), keywords: ["add host", "enroll"] },
      { id: "maintenance", label: "Maintenance windows", icon: Wrench, action: () => navigate("/maintenance"), keywords: ["downtime", "patching", "suppress"] },
      { id: "alerts", label: "Search alerts", icon: Bell, action: () => navigate("/alerts"), keywords: ["triage", "open"] },
      { id: "offenses", label: "Go to Offenses", icon: ShieldAlert, action: () => navigate("/offenses") },
      { id: "search", label: "SIEM Search", icon: Search, action: () => navigate("/search"), keywords: ["query", "siem"] },
      { id: "sim", label: "Run simulation", icon: FlaskConical, action: () => navigate("/simulation"), keywords: ["attack", "lab", "demo"] },
    ],
    [navigate],
  );

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
      if (e.key === "Escape") {
        setOpen(false);
        setQuery("");
      }
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

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4">
      <button
        type="button"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        aria-label="Close command palette"
        onClick={() => setOpen(false)}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative w-full max-w-lg rounded-xl border border-border bg-card shadow-2xl overflow-hidden animate-scale-in"
      >
        <p id={titleId} className="sr-only">
          Command palette
        </p>
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
      </div>
    </div>
  );
}
