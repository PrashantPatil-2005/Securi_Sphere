"use client";

import { memo, useState, useCallback } from "react";
import { ChevronRight, ChevronDown, Clock } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Card, CardHeader, SeverityBadge } from "@/components/design-system";
import type { AlertEvent } from "@/lib/types/alert";

interface AlertRelatedEventsProps {
  events: AlertEvent[];
  onSelectEvent: (event: AlertEvent) => void;
}

function formatEventTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function EventRow({
  event,
  onSelect,
}: {
  event: AlertEvent;
  onSelect: (event: AlertEvent) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const handleToggle = useCallback(() => {
    setExpanded((prev) => {
      const next = !prev;
      if (next) onSelect(event);
      return next;
    });
  }, [event, onSelect]);

  return (
    <button
      type="button"
      onClick={handleToggle}
      className={cn(
        "w-full text-left border-b border-border-subtle last:border-b-0",
        "px-3 py-2.5 hover:bg-[var(--sidebar-hover)] transition-colors",
        "focus:outline-none focus-visible:ring-1 focus-visible:ring-accent",
      )}
    >
      <div className="flex items-center gap-2">
        <span className="text-muted shrink-0">
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </span>

        <SeverityBadge severity={event.severity} className="shrink-0" />

        <span className="code-text shrink-0">{event.event_type}</span>

        {event.description && (
          <span className="text-xs text-muted truncate flex-1 min-w-0">
            {event.description}
          </span>
        )}

        <div className="flex items-center gap-1 text-[10px] text-muted shrink-0 tabular-nums">
          <Clock className="w-3 h-3" />
          {formatEventTime(event.timestamp)}
        </div>
      </div>

      {expanded && event.description && (
        <div className="mt-2 ml-6 text-xs text-foreground/80 leading-relaxed">
          {event.description}
        </div>
      )}
    </button>
  );
}

function AlertRelatedEventsInner({
  events,
  onSelectEvent,
}: AlertRelatedEventsProps) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  );

  return (
    <Card>
      <CardHeader
        title="Related Events"
        subtitle={events.length > 0 ? `${events.length} events in investigation window` : undefined}
      />
      <div>
        {sorted.length === 0 ? (
          <div className="py-10 text-center text-sm text-muted">
            No related events found in the &plusmn;30min window.
          </div>
        ) : (
          sorted.map((event) => (
            <EventRow
              key={event.id}
              event={event}
              onSelect={onSelectEvent}
            />
          ))
        )}
      </div>
    </Card>
  );
}

export const AlertRelatedEvents = memo(AlertRelatedEventsInner);
