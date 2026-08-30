"use client";

import { memo } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";

interface HostEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp: string;
  source: string | null;
}

interface HostActivityListProps {
  events: HostEvent[];
  hostId: string;
  total?: number;
  isLoading: boolean;
}

function formatTimestamp(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return ts;
  }
}

function HostActivityListInner({ events, hostId, total = 0, isLoading }: HostActivityListProps) {
  return (
    <Card>
      <CardHeader
        title="Recent Activity"
        subtitle={`${total.toLocaleString()} events`}
        action={
          <Link
            href={`/events?host_id=${hostId}`}
            className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
          >
            View all
            <ExternalLink className="w-3 h-3" />
          </Link>
        }
      />
      <div className="divide-y divide-border-subtle">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-3 w-16 skeleton rounded" />
                <div className="h-3 w-12 skeleton rounded" />
                <div className="h-3 flex-1 skeleton rounded" />
              </div>
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="p-4 text-sm text-muted">No recent events.</div>
        ) : (
          events.map((event) => (
            <div key={event.id} className="flex items-center gap-3 px-4 py-2 hover:bg-[var(--sidebar-hover)] transition-colors">
              <span className="text-[11px] text-muted tabular-nums font-mono shrink-0 w-16">
                {formatTimestamp(event.timestamp)}
              </span>
              <SeverityBadge severity={event.severity} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="font-mono text-xs text-accent">{event.event_type}</span>
                {event.description && (
                  <p className="text-[11px] text-muted truncate">{event.description}</p>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

export const HostActivityList = memo(HostActivityListInner);
