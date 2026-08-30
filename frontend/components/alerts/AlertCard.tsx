"use client";

import { memo, useMemo } from "react";
import { cn } from "@/lib/utils/cn";
import { SeverityBadge, StatusBadge } from "@/components/design-system/Badge";
import type { Alert } from "@/lib/types/alert";

interface AlertCardProps {
  alert: Alert;
  hostName?: string;
  selected?: boolean;
  checked?: boolean;
  showCheckbox?: boolean;
  onSelect?: (id: string) => void;
  onToggle?: (id: string, next: boolean) => void;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

function AlertCardInner({
  alert,
  hostName,
  selected,
  checked,
  showCheckbox,
  onSelect,
  onToggle,
}: AlertCardProps) {
  const relativeTime = useMemo(
    () => formatRelativeTime(alert.created_at),
    [alert.created_at],
  );

  return (
    <div
      className={cn(
        "panel p-3 transition-colors duration-150 hover:border-border cursor-pointer",
        selected && "border-accent/40 bg-accent/5",
        "border-l-2",
        `border-l-severity-${alert.severity}`,
      )}
      onClick={() => onSelect?.(alert.id)}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect?.(alert.id);
        }
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          {showCheckbox && (
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => {
                e.stopPropagation();
                onToggle?.(alert.id, e.target.checked);
              }}
              onClick={(e) => e.stopPropagation()}
              className="w-3.5 h-3.5 rounded border-border accent-accent shrink-0"
              aria-label={`Select alert ${alert.title}`}
            />
          )}
          <SeverityBadge severity={alert.severity} />
          <StatusBadge status={alert.status} />
        </div>
        <span className="text-[11px] text-muted tabular-nums shrink-0">
          {relativeTime}
        </span>
      </div>

      <p className="text-sm font-medium text-foreground truncate mb-0.5">
        {alert.title}
      </p>
      {alert.description && (
        <p className="text-xs text-muted truncate mb-2">{alert.description}</p>
      )}

      <div className="flex items-center gap-3 text-[11px] text-muted">
        {hostName && <span className="truncate">{hostName}</span>}
        {alert.confidence != null && (
          <span className="tabular-nums">{Math.round(alert.confidence * 100)}%</span>
        )}
        {alert.source && (
          <span className="font-mono truncate">{alert.source}</span>
        )}
      </div>
    </div>
  );
}

export const AlertCard = memo(AlertCardInner);
