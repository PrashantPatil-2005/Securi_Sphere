"use client";

import { memo } from "react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";
import { EmptyState } from "@/components/design-system/EmptyState";
import type { Timeline, TimelineEvent } from "@/lib/types/timeline";

interface TimelineDetailProps {
  timeline: Timeline | null;
  events: TimelineEvent[];
  isLoading: boolean;
  currentIndex: number;
}

function formatTime(ts: string): string {
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

function TimelineDetailInner({ timeline, events, isLoading, currentIndex }: TimelineDetailProps) {
  if (!timeline) {
    return (
      <Card className="min-h-[400px] flex items-center justify-center">
        <EmptyState
          title="Select a timeline"
          description="Choose an attack chain from the list to replay its events."
        />
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title={timeline.title}
        subtitle={timeline.description ?? `${events.length} events in chain`}
      />
      <div className="p-4">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex gap-3">
                <div className="h-3 w-16 skeleton rounded" />
                <div className="h-3 flex-1 skeleton rounded" />
              </div>
            ))}
          </div>
        ) : events.length === 0 ? (
          <p className="text-sm text-muted">No events in this timeline.</p>
        ) : (
          <div className="relative pl-6 space-y-0 max-h-[500px] overflow-y-auto">
            {events.map((e, i) => {
              const active = i === currentIndex;
              const revealed = i <= currentIndex;
              return (
                <div
                  key={e.id}
                  className={`relative pb-5 last:pb-0 transition-opacity duration-300 ${
                    !revealed ? "opacity-30" : ""
                  }`}
                >
                  {i < events.length - 1 && (
                    <div
                      className={`absolute left-[5px] top-3 bottom-0 w-px ${
                        i < currentIndex ? "bg-accent/50" : "bg-border-subtle"
                      }`}
                    />
                  )}
                  <div
                    className={`absolute left-0 top-1.5 w-2.5 h-2.5 rounded-full ring-4 transition-all duration-300 ${
                      active
                        ? "bg-accent ring-accent/30 scale-125"
                        : i < currentIndex
                          ? "bg-accent/80 ring-accent/15"
                          : "bg-border-subtle ring-transparent"
                    }`}
                  />
                  <div
                    className={`ml-4 rounded-lg p-3 border transition-colors ${
                      active ? "border-accent/40 bg-accent/5" : "border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted tabular-nums font-mono">
                        {formatTime(e.timestamp)}
                      </span>
                      <SeverityBadge severity={e.severity} />
                      {e.mitre_technique_id && (
                        <span className="text-[10px] font-mono text-accent">
                          {e.mitre_technique_id}
                        </span>
                      )}
                    </div>
                    <p className="font-medium text-sm mt-1 font-mono text-foreground">{e.event_type}</p>
                    {e.description && (
                      <p className="text-xs text-muted mt-0.5">{e.description}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

export const TimelineDetail = memo(TimelineDetailInner);
