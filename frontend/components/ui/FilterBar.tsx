"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, SlidersHorizontal } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface FilterBarProps {
  children: ReactNode;
  more?: ReactNode;
  activeCount?: number;
  className?: string;
}

export function FilterBar({ children, more, activeCount = 0, className }: FilterBarProps) {
  const [expanded, setExpanded] = useState(false);
  const hasMore = !!more;

  return (
    <div className={cn("mb-4 space-y-2", className)}>
      <div className="filter-bar items-end">
        {children}
        {hasMore && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className={cn(
              "btn-ghost text-xs shrink-0 inline-flex items-center gap-1.5",
              (expanded || activeCount > 0) && "border-accent/40 text-accent",
            )}
            aria-expanded={expanded}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" aria-hidden />
            More filters
            {activeCount > 0 && (
              <span className="min-w-[1.25rem] h-5 px-1 rounded-full bg-accent/20 text-[10px] font-semibold tabular-nums">
                {activeCount}
              </span>
            )}
            <ChevronDown className={cn("w-3.5 h-3.5 transition-transform", expanded && "rotate-180")} aria-hidden />
          </button>
        )}
      </div>
      {hasMore && expanded && (
        <div className="filter-bar p-3 rounded-lg border border-border-subtle bg-[var(--sidebar-hover)]/50 animate-fade-in">
          {more}
        </div>
      )}
    </div>
  );
}
