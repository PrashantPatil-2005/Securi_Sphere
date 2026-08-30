"use client";

import { memo } from "react";
import { ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Card, CardHeader, EmptyState, TimelineItem } from "@/components/design-system";
import type { AlertTimeline } from "@/lib/types/alert";

interface AlertAttackStoryProps {
  timelines: AlertTimeline[];
  hostId: string;
}

function formatTimelineTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function AlertAttackStoryInner({ timelines }: AlertAttackStoryProps) {
  const sorted = [...timelines].sort(
    (a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime(),
  );

  return (
    <Card>
      <CardHeader
        title="Attack Chain"
        subtitle={timelines.length > 0 ? `${timelines.length} correlated events` : undefined}
      />
      <div className="p-4">
        {sorted.length === 0 ? (
          <EmptyState
            title="No correlated attack chain detected for this host."
            icon={<ShieldAlert className="w-6 h-6" />}
          />
        ) : (
          <div>
            {sorted.map((timeline, i) => {
              const severityKey = (timeline.severity?.toLowerCase() || "info") as
                | "critical"
                | "high"
                | "medium"
                | "low"
                | "info";

              return (
                <TimelineItem
                  key={timeline.id}
                  severity={severityKey}
                  title={timeline.title}
                  timestamp={formatTimelineTime(timeline.started_at)}
                  className={cn(i === sorted.length - 1 && "pb-0")}
                >
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={cn(
                        "text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded",
                        timeline.status === "active"
                          ? "bg-accent/10 text-accent"
                          : "bg-card-elevated text-muted",
                      )}
                    >
                      {timeline.status}
                    </span>
                    <span className="text-[10px] text-muted tabular-nums">
                      {timeline.confidence}% confidence
                    </span>
                  </div>
                </TimelineItem>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

export const AlertAttackStory = memo(AlertAttackStoryInner);
