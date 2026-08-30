"use client";

import { TimelineItem } from "@/components/design-system/TimelineItem";
import type { OffenseTimelineEntry } from "@/lib/types/offense";

interface Props {
  timeline: OffenseTimelineEntry[];
}

export function OffenseTimeline({ timeline }: Props) {
  if (!timeline.length) {
    return (
      <div className="p-4 rounded-xl border border-border-subtle bg-surface">
        <p className="text-xs text-muted">No timeline data available.</p>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <h3 className="text-sm font-semibold mb-3">Attack Timeline</h3>
      <div className="space-y-0">
        {timeline.map((entry, i) => (
          <TimelineItem
            key={i}
            timestamp={entry.ts}
            title={entry.type}
            description={entry.detail}
          />
        ))}
      </div>
    </div>
  );
}
