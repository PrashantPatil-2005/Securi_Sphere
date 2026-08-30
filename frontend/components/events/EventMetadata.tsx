"use client";

import { memo } from "react";
import { SeverityBadge } from "@/components/design-system/Badge";
import type { EventSummary } from "@/lib/types/event";

interface EventMetadataProps {
  event: EventSummary;
}

function formatFullTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      fractionalSecondDigits: 3,
    });
  } catch {
    return ts;
  }
}

function formatRelativeTime(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function MetaRow({ label, children, mono }: { label: string; children: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-start gap-3 py-1.5">
      <span className="text-xs text-muted w-24 shrink-0">{label}</span>
      <span className={`text-sm text-foreground ${mono ? "font-mono" : ""}`}>{children}</span>
    </div>
  );
}

function EventMetadataInner({ event }: EventMetadataProps) {
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Event Details</h4>

      <MetaRow label="Event type">
        <code className="text-xs font-mono bg-card-elevated px-2 py-0.5 rounded border border-border-subtle">
          {event.event_type}
        </code>
      </MetaRow>

      <MetaRow label="Severity">
        <SeverityBadge severity={event.severity} />
      </MetaRow>

      <MetaRow label="Timestamp" mono>
        <div>
          <div>{formatFullTimestamp(event.timestamp)}</div>
          <div className="text-xs text-muted mt-0.5">{formatRelativeTime(event.timestamp)}</div>
        </div>
      </MetaRow>

      {event.source && (
        <MetaRow label="Source" mono>
          {event.source}
        </MetaRow>
      )}

      <MetaRow label="Host ID" mono>
        <span className="text-xs" title={event.host_id}>{event.host_id}</span>
      </MetaRow>

      <MetaRow label="Event ID" mono>
        <span className="text-xs" title={event.id}>{event.id}</span>
      </MetaRow>

      {event.description && (
        <div className="pt-2">
          <span className="text-xs text-muted block mb-1">Description</span>
          <p className="text-sm text-foreground leading-relaxed">{event.description}</p>
        </div>
      )}
    </div>
  );
}

export const EventMetadata = memo(EventMetadataInner);
