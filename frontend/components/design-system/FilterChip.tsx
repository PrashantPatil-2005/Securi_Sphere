"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface FilterChipProps {
  label: string;
  value?: string;
  active?: boolean;
  onClick?: () => void;
  onClear?: () => void;
  className?: string;
}

export function FilterChip({
  label,
  value,
  active,
  onClick,
  onClear,
  className,
}: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border transition-colors",
        active
          ? "bg-accent/10 text-accent border-accent/30"
          : "text-muted border-border-subtle hover:border-border hover:text-foreground",
        className,
      )}
    >
      {label}
      {value && <span className="text-muted">{value}</span>}
      {active && onClear && (
        <span
          role="button"
          tabIndex={0}
          onClick={(e) => {
            e.stopPropagation();
            onClear();
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.stopPropagation();
              onClear();
            }
          }}
          className="ml-0.5 hover:text-foreground"
          aria-label={`Clear ${label} filter`}
        >
          &times;
        </span>
      )}
    </button>
  );
}

interface FilterGroupProps {
  children: ReactNode;
  label?: string;
  className?: string;
}

export function FilterGroup({ children, label, className }: FilterGroupProps) {
  return (
    <div className={cn("flex flex-wrap gap-2", className)}>
      {label && (
        <span className="text-xs font-medium text-muted self-center mr-1">
          {label}
        </span>
      )}
      {children}
    </div>
  );
}
