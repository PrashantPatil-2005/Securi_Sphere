"use client";

import { memo, useMemo } from "react";
import { cn } from "@/lib/utils/cn";
import { SeverityBadge } from "@/components/design-system/Badge";
import { StatusBadge } from "@/components/design-system/Badge";
import type { Alert } from "@/lib/types/alert";

interface AlertRowProps {
  alert: Alert;
  hostName?: string;
  selected?: boolean;
  onClick?: () => void;
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

function AlertRowInner({ alert, hostName, selected, onClick }: AlertRowProps) {
  const relativeTime = useMemo(
    () => formatRelativeTime(alert.created_at),
    [alert.created_at],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      className={cn(
        "data-table-row w-full text-left gap-3 cursor-pointer",
        selected && "bg-accent/5 border-l-2 border-l-accent",
      )}
    >
      <div className="data-table-cell w-[90px] shrink-0">
        <SeverityBadge severity={alert.severity} />
      </div>

      <div className="data-table-cell w-[110px] shrink-0">
        <StatusBadge status={alert.status} />
      </div>

      <div className="data-table-cell flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {alert.title}
        </p>
        {alert.description && (
          <p className="text-xs text-muted truncate mt-0.5">
            {alert.description}
          </p>
        )}
      </div>

      <div className="data-table-cell w-[120px] shrink-0 text-xs text-muted truncate">
        {hostName || "—"}
      </div>

      {alert.confidence != null && (
        <div className="data-table-cell w-[70px] shrink-0 text-xs text-muted tabular-nums text-right">
          {Math.round(alert.confidence * 100)}%
        </div>
      )}

      {alert.source && (
        <div className="data-table-cell w-[100px] shrink-0 text-[11px] text-muted truncate font-mono">
          {alert.source}
        </div>
      )}

      <div className="data-table-cell w-[80px] shrink-0 text-xs text-muted tabular-nums text-right">
        {relativeTime}
      </div>
    </div>
  );
}

export const AlertRow = memo(AlertRowInner);
