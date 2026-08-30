"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { SeverityBadge } from "@/components/design-system/Badge";
import { Button } from "@/components/design-system/Button";
import type { OffenseEventRef } from "@/lib/types/offense";

interface Props {
  events: OffenseEventRef[];
}

export function OffenseEventsList({ events }: Props) {
  const [expanded, setExpanded] = useState(false);
  const displayEvents = expanded ? events : events.slice(0, 10);

  if (!events.length) {
    return (
      <div className="p-4 rounded-xl border border-border-subtle bg-surface">
        <p className="text-xs text-muted">No related events.</p>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <h3 className="text-sm font-semibold mb-3">Related Events ({events.length})</h3>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {displayEvents.map((e) => (
          <div key={e.id} className="flex items-center gap-2 p-2 rounded text-xs font-mono">
            <SeverityBadge severity={e.severity} />
            <span className="text-muted shrink-0">{new Date(e.timestamp).toLocaleTimeString()}</span>
            <span className="font-medium">{e.event_type}</span>
            {e.description && (
              <span className="text-muted truncate">{e.description}</span>
            )}
          </div>
        ))}
      </div>
      {events.length > 10 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(!expanded)}
          className="mt-2"
        >
          <ChevronDown
            className="w-3 h-3 mr-1"
            style={expanded ? { transform: "rotate(180deg)" } : undefined}
          />
          {expanded ? "Show less" : `Show all ${events.length} events`}
        </Button>
      )}
    </div>
  );
}
