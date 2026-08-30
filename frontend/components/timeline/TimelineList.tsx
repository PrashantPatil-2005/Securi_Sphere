"use client";

import { memo } from "react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";
import type { Timeline } from "@/lib/types/timeline";
import { timelineDuration } from "@/lib/types/timeline";

interface TimelineListProps {
  timelines: Timeline[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  isLoading: boolean;
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

function formatDate(ts: string): string {
  try {
    return new Date(ts).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return ts;
  }
}

function TimelineListItem({ timeline, isSelected, onSelect }: {
  timeline: Timeline;
  isSelected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(timeline.id)}
      className={`w-full text-left px-4 py-3 border-b border-border-subtle hover:bg-[var(--sidebar-hover)] transition-colors ${
        isSelected ? "bg-accent/5 border-l-2 border-l-accent" : "border-l-2 border-l-transparent"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-foreground truncate">{timeline.title}</p>
          {timeline.description && (
            <p className="text-xs text-muted mt-0.5 line-clamp-2">{timeline.description}</p>
          )}
        </div>
        <SeverityBadge severity={timeline.severity} className="shrink-0" />
      </div>
      <div className="flex items-center gap-3 mt-2 text-[10px] text-muted">
        <span className="tabular-nums">{formatDate(timeline.started_at)}</span>
        <span className="tabular-nums">{formatTime(timeline.started_at)}</span>
        <span className="text-accent tabular-nums">{timelineDuration(timeline.started_at, timeline.ended_at)}</span>
        <span className="tabular-nums">{timeline.confidence.toFixed(0)}%</span>
      </div>
      {timeline.mitre_techniques.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {timeline.mitre_techniques.slice(0, 3).map((m) => (
            <span key={m} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
              {m}
            </span>
          ))}
          {timeline.mitre_techniques.length > 3 && (
            <span className="text-[9px] text-muted">+{timeline.mitre_techniques.length - 3}</span>
          )}
        </div>
      )}
    </button>
  );
}

function TimelineListInner({ timelines, selectedId, onSelect, isLoading }: TimelineListProps) {
  return (
    <Card>
      <CardHeader
        title="Attack Timelines"
        subtitle={`${timelines.length} chain${timelines.length !== 1 ? "s" : ""} detected`}
      />
      <div className="divide-y divide-border-subtle max-h-[600px] overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 w-3/4 skeleton rounded" />
                <div className="h-3 w-1/2 skeleton rounded" />
              </div>
            ))}
          </div>
        ) : timelines.length === 0 ? (
          <div className="p-4 text-sm text-muted">No attack timelines in this range.</div>
        ) : (
          timelines.map((t) => (
            <TimelineListItem
              key={t.id}
              timeline={t}
              isSelected={selectedId === t.id}
              onSelect={onSelect}
            />
          ))
        )}
      </div>
    </Card>
  );
}

export const TimelineList = memo(TimelineListInner);
