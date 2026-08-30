"use client";

import { memo, useCallback } from "react";
import { SeverityBadge } from "@/components/design-system/Badge";
import type { EventSummary } from "@/lib/types/event";

interface EventRowProps {
  event: EventSummary;
  selected: boolean;
  onClick: (event: EventSummary) => void;
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return ts;
  }
}

function EventRowInner({ event, selected, onClick }: EventRowProps) {
  const handleClick = useCallback(() => onClick(event), [event, onClick]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`w-full text-left px-3 py-2.5 border-b border-border-subtle hover:bg-[var(--sidebar-hover)] transition-colors ${
        selected ? "bg-accent/5 border-l-2 border-l-accent" : "border-l-2 border-l-transparent"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Timestamp */}
        <span className="text-[11px] text-muted tabular-nums font-mono shrink-0 pt-0.5 w-[68px]">
          {formatTimestamp(event.timestamp)}
        </span>

        {/* Severity */}
        <SeverityBadge severity={event.severity} className="shrink-0 mt-0.5" />

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-mono text-xs text-accent font-medium truncate">
              {event.event_type}
            </span>
            {event.source && (
              <span className="text-[10px] text-muted bg-card-elevated px-1.5 py-0.5 rounded">
                {event.source}
              </span>
            )}
          </div>
          {event.description && (
            <p className="text-xs text-muted line-clamp-1">{event.description}</p>
          )}
        </div>

        {/* Host ID (truncated) */}
        <span className="text-[10px] text-muted font-mono shrink-0 hidden lg:block" title={event.host_id}>
          {event.host_id.slice(0, 8)}
        </span>
      </div>
    </button>
  );
}

export const EventRow = memo(EventRowInner);
