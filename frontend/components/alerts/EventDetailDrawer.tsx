"use client";

import { useCallback, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Clock } from "lucide-react";
import { Drawer } from "@/components/ui/Drawer";
import { SeverityBadge } from "@/components/design-system/Badge";
import type { AlertEvent } from "@/lib/types/alert";

interface EventDetailDrawerProps {
  event: AlertEvent | null;
  open: boolean;
  onClose: () => void;
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

function JsonValue({ value }: { value: unknown }): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted italic">null</span>;
  }
  if (typeof value === "boolean") {
    return <span className="text-accent">{String(value)}</span>;
  }
  if (typeof value === "number") {
    return <span className="text-severity-high">{value}</span>;
  }
  if (typeof value === "string") {
    return <span className="text-severity-low">{value}</span>;
  }
  return <span className="text-muted">{JSON.stringify(value)}</span>;
}

function JsonKey({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-severity-medium font-medium">
      {children}
      <span className="text-muted">: </span>
    </span>
  );
}

function CollapsibleJson({ label, data }: { label: string; data: unknown }) {
  const [expanded, setExpanded] = useState(true);

  const entries = useMemo(() => {
    if (data === null || data === undefined) return [];
    if (typeof data === "object" && !Array.isArray(data)) return Object.entries(data as Record<string, unknown>);
    if (Array.isArray(data)) return (data as unknown[]).map((v, i) => [String(i), v] as const);
    return [];
  }, [data]);

  if (entries.length === 0) return null;

  return (
    <div className="border border-border-subtle rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center gap-2 w-full px-3 py-2 text-xs font-medium text-foreground bg-card-elevated hover:bg-card transition-colors text-left"
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-muted shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-muted shrink-0" />
        )}
        {label}
        <span className="ml-auto text-muted tabular-nums">{entries.length} keys</span>
      </button>
      {expanded && (
        <div className="p-3 bg-card font-mono text-xs leading-relaxed max-h-96 overflow-y-auto">
          {entries.map(([key, value]) => (
            <div key={key} className="flex gap-0 py-0.5">
              <JsonKey>{key}</JsonKey>
              <span className="ml-1">
                {typeof value === "object" && value !== null ? (
                  <CollapsibleJson label={key} data={value} />
                ) : (
                  <JsonValue value={value} />
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EventDataSection({ event }: { event: AlertEvent }) {
  const [expanded, setExpanded] = useState(true);

  const eventKeys = useMemo(() => {
    const skip = new Set(["id", "event_type", "severity", "description", "timestamp"]);
    return Object.entries(event).filter(([k]) => !skip.has(k));
  }, [event]);

  const hasExtraData = eventKeys.length > 0;

  if (!hasExtraData) return null;

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center gap-2 w-full text-left group"
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-muted shrink-0 transition-transform group-hover:text-foreground" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-muted shrink-0 transition-transform group-hover:text-foreground" />
        )}
        <span className="text-xs font-medium text-muted uppercase tracking-wide">
          Full Event Data
        </span>
      </button>
      {expanded && (
        <div className="space-y-2">
          {eventKeys.map(([key, value]) => (
            <CollapsibleJson key={key} label={key} data={value} />
          ))}
        </div>
      )}
    </div>
  );
}

export function EventDetailDrawer({ event, open, onClose }: EventDetailDrawerProps) {
  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  return (
    <Drawer
      open={open}
      onClose={handleClose}
      title="Event Details"
      description={event?.event_type}
    >
      {event && (
        <div className="space-y-5">
          {/* Event Type + Severity */}
          <div className="flex items-center gap-3">
            <code className="text-sm font-mono font-semibold text-foreground bg-card-elevated px-2.5 py-1 rounded border border-border-subtle">
              {event.event_type}
            </code>
            <SeverityBadge severity={event.severity} />
          </div>

          {/* Timestamp */}
          <div className="flex items-center gap-2 text-sm text-muted">
            <Clock className="w-3.5 h-3.5 shrink-0" />
            <div>
              <div className="tabular-nums">
                {new Date(event.timestamp).toLocaleString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  fractionalSecondDigits: 3,
                })}
              </div>
              <div className="text-xs text-muted mt-0.5">{formatRelativeTime(event.timestamp)}</div>
            </div>
          </div>

          {/* Description */}
          {event.description && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-medium text-muted uppercase tracking-wide">Description</h4>
              <p className="text-sm text-foreground leading-relaxed">{event.description}</p>
            </div>
          )}

          {/* Separator */}
          <div className="border-t border-border-subtle" />

          {/* Full Event Data */}
          <EventDataSection event={event} />
        </div>
      )}
    </Drawer>
  );
}
