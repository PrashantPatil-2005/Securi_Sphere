"use client";

import { memo, useMemo } from "react";
import { Clock } from "lucide-react";
import { TimelineItem } from "@/components/design-system/TimelineItem";
import type { EventSummary } from "@/lib/types/event";

interface EventTimelineProps {
  events: EventSummary[];
  selectedId: string | null;
  onSelect: (event: EventSummary) => void;
}

function EventTimelineInner({ events, selectedId, onSelect }: EventTimelineProps) {
  const sorted = useMemo(
    () => [...events].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [events],
  );

  if (sorted.length === 0) {
    return (
      <div className="text-xs text-muted italic py-2">
        No timeline events available.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="w-3.5 h-3.5 text-muted" />
        <h4 className="text-xs font-medium text-muted uppercase tracking-wide">
          Event Timeline ({sorted.length})
        </h4>
      </div>
      <div className="space-y-0.5">
        {sorted.map((event) => (
          <button
            key={event.id}
            type="button"
            onClick={() => onSelect(event)}
            className={`w-full text-left transition-colors rounded ${
              event.id === selectedId
                ? "bg-accent/10"
                : "hover:bg-[var(--sidebar-hover)]"
            }`}
          >
            <TimelineItem
              severity={event.severity as "critical" | "high" | "medium" | "low" | "info"}
              title={event.event_type}
              description={event.description ?? undefined}
              timestamp={new Date(event.timestamp).toLocaleTimeString(undefined, {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false,
              })}
            />
          </button>
        ))}
      </div>
    </div>
  );
}

export const EventTimeline = memo(EventTimelineInner);
