"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

export interface TabItem<T extends string = string> {
  id: T;
  label: string;
  disabled?: boolean;
  panelId?: string;
}

type TabVariant = "underline" | "pill" | "sidebar";

interface TabsProps<T extends string> {
  tabs: TabItem<T>[];
  active: T;
  onChange: (id: T) => void;
  className?: string;
  ariaLabel?: string;
  variant?: TabVariant;
}

const variantStyles: Record<TabVariant, { list: string; tab: (active: boolean) => string }> = {
  underline: {
    list: "flex gap-1 border-b border-border-subtle",
    tab: (active) =>
      cn(
        "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
        active
          ? "border-accent text-accent"
          : "border-transparent text-muted hover:text-foreground",
      ),
  },
  pill: {
    list: "flex flex-wrap gap-2",
    tab: (active) =>
      cn(
        "px-3 py-1.5 rounded-md text-sm font-medium border border-transparent transition-colors",
        active
          ? "bg-accent/10 text-accent border-accent/30"
          : "text-muted hover:text-foreground hover:bg-[var(--sidebar-hover)]",
      ),
  },
  sidebar: {
    list: "flex lg:flex-col gap-1",
    tab: (active) =>
      cn(
        "px-3 py-2 rounded-md text-body font-medium text-left whitespace-nowrap transition-colors",
        active
          ? "bg-[var(--sidebar-active)] text-accent"
          : "text-muted hover:text-foreground hover:bg-[var(--sidebar-hover)]",
      ),
  },
};

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
  className,
  ariaLabel = "Tabs",
  variant = "underline",
}: TabsProps<T>) {
  const styles = variantStyles[variant];

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      aria-orientation={variant === "sidebar" ? "vertical" : "horizontal"}
      className={cn(styles.list, className)}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          id={`tab-${tab.id}`}
          aria-selected={active === tab.id}
          aria-controls={tab.panelId}
          disabled={tab.disabled}
          onClick={() => onChange(tab.id)}
          className={cn(styles.tab(active === tab.id), tab.disabled && "opacity-50 cursor-not-allowed")}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function TabPanel({
  id,
  labelledBy,
  children,
  className,
}: {
  id: string;
  labelledBy?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div role="tabpanel" id={id} aria-labelledby={labelledBy} className={className}>
      {children}
    </div>
  );
}
