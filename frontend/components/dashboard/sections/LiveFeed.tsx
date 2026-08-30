"use client";

import { memo } from "react";
import { useSecurityFeedStore, useFeedItems } from "@/lib/websocket";
import { EmptyState } from "@/components/design-system/EmptyState";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface FeedItem {
  id?: string;
  timestamp?: string;
  host_name?: string;
  host_id?: string;
  severity?: string;
  event_type?: string;
  description?: string;
  title?: string;
  _type?: string;
  _ts?: number;
}

function timeAgo(dateStr?: string): string {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 5) return "now";
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h`;
}

const severityColor: Record<string, string> = {
  critical: "border-l-severity-critical",
  high: "border-l-severity-high",
  medium: "border-l-severity-medium",
  low: "border-l-severity-low",
  info: "border-l-severity-info",
};

const severityTextClass: Record<string, string> = {
  critical: "text-[10px] font-medium severity-critical",
  high: "text-[10px] font-medium severity-high",
  medium: "text-[10px] font-medium severity-medium",
  low: "text-[10px] font-medium severity-low",
  info: "text-[10px] font-medium severity-info",
};

export const LiveFeed = memo(function LiveFeed() {
  const { subscribe, getSnapshot } = useSecurityFeedStore(30);
  const rawItems = useFeedItems(subscribe, getSnapshot);
  const items = rawItems as unknown as FeedItem[];

  if (!items.length) {
    return (
      <EmptyState
        title="Waiting for events"
        description="Real-time security events will appear here as they arrive."
        icon={<Activity className="w-7 h-7" />}
      />
    );
  }

  return (
    <div className="space-y-0.5 max-h-[320px] overflow-y-auto">
      {items.map((item, i) => (
        <div
          key={item._ts ?? item.id ?? i}
          className={cn(
            "flex items-start gap-2.5 px-3 py-2 rounded-md border-l-2 hover:bg-[var(--sidebar-hover)] transition-colors",
            severityColor[item.severity || "info"] || "border-l-severity-info",
            item._ts && Date.now() - item._ts < 5000 && "feed-row-new",
          )}
        >
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-foreground truncate">
              {item.title || item.description || item.event_type || "Event"}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              {item.host_name && (
                <span className="text-[10px] text-muted">{item.host_name}</span>
              )}
              {item.severity && (
                <>
                  <span className="text-[9px] text-muted">·</span>
                  <span className={severityTextClass[item.severity] || "text-[10px] font-medium severity-info"}>
                    {item.severity}
                  </span>
                </>
              )}
            </div>
          </div>
          <span className="text-[10px] text-muted tabular-nums shrink-0">
            {timeAgo(item.timestamp)}
          </span>
        </div>
      ))}
    </div>
  );
});
