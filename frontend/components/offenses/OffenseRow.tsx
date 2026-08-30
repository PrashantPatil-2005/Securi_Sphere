"use client";

import { memo } from "react";
import { SeverityBadge, StatusBadge } from "@/components/design-system/Badge";
import { cn } from "@/lib/utils/cn";
import type { OffenseSummary } from "@/lib/types/offense";

interface Props {
  offense: OffenseSummary;
  selected: boolean;
  onClick: () => void;
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export const OffenseRow = memo(function OffenseRow({ offense, selected, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full text-left p-3 rounded-lg border transition-colors",
        selected
          ? "border-accent bg-accent/10"
          : "border-border-subtle hover:bg-surface-hover",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <SeverityBadge severity={offense.risk_level} />
            <span className="font-mono text-xs text-muted">#{offense.offense_number}</span>
            <StatusBadge status={offense.status} />
          </div>
          <p className="font-medium text-sm truncate">{offense.title}</p>
          <div className="flex items-center gap-2 mt-1 text-xs text-muted">
            <span>{offense.host_name}</span>
            <span>·</span>
            <span>{offense.alert_count} alert{offense.alert_count !== 1 ? "s" : ""}</span>
            <span>·</span>
            <span>{offense.event_count} event{offense.event_count !== 1 ? "s" : ""}</span>
            <span>·</span>
            <span>{formatRelativeTime(offense.updated_at)}</span>
          </div>
        </div>
        {offense.incident_id && (
          <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-medium">
            Case
          </span>
        )}
      </div>
    </button>
  );
});
