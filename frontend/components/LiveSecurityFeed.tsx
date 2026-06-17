"use client";

import { memo, useEffect } from "react";
import { useSecurityFeedStore, useFeedItems } from "@/lib/websocket";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

export interface FeedItem {
  id?: string;
  timestamp?: string;
  host_name?: string;
  host_id?: string;
  severity?: string;
  event_type?: string;
  description?: string | null;
  title?: string;
  _type?: string;
}

interface Props {
  initial?: FeedItem[];
  maxItems?: number;
}

function FeedRow({ item }: { item: FeedItem }) {
  const ts = item.timestamp || new Date().toISOString();
  const label = item.event_type || (item._type === "new_alert" ? "alert" : "event");
  const text = item.description || item.title || "";
  return (
    <div className="flex gap-3 py-1.5 border-b border-[var(--border-subtle)]/60 text-[13px] font-mono">
      <span className="text-[var(--muted)] shrink-0 w-16">{new Date(ts).toLocaleTimeString()}</span>
      <span className="text-[var(--accent)] shrink-0 w-20 truncate">{item.host_name || item.host_id?.slice(0, 8)}</span>
      <SeverityBadge severity={item.severity || "info"} />
      <span className="truncate text-[var(--foreground)]">{label}: {text}</span>
    </div>
  );
}

const FeedRowMemo = memo(FeedRow);

function LiveSecurityFeedInner({ initial = [], maxItems = 50 }: Props) {
  const { subscribe, getSnapshot, prepend } = useSecurityFeedStore(maxItems);
  const liveItems = useFeedItems(subscribe, getSnapshot) as FeedItem[];

  useEffect(() => {
    if (initial.length) prepend(initial as Array<Record<string, unknown>>);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- seed once

  const items = liveItems.length > 0 ? liveItems : initial;

  if (items.length === 0) {
    return <p className="empty-desc py-4">No recent security events. Live updates appear here.</p>;
  }

  return (
    <div className="max-h-80 overflow-y-auto">
      {items.map((e, i) => (
        <FeedRowMemo key={e.id || `feed-${i}`} item={e} />
      ))}
    </div>
  );
}

export default memo(LiveSecurityFeedInner);
