"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Radio } from "lucide-react";
import { api } from "@/lib/api";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { useFeedItems, useSecurityFeedStore } from "@/lib/websocket";
import { cn } from "@/lib/utils/cn";
import type { EventListResponse } from "@/lib/types/event";

const MAX_LINES = 60;
const SEED_LIMIT = 30;

const SEVERITY_TEXT: Record<string, string> = {
  critical: "text-[var(--danger)]",
  high: "text-[var(--danger)]",
  medium: "text-[var(--warning)]",
  low: "text-[var(--muted)]",
  info: "text-[var(--muted)]",
};

interface FeedItem {
  id?: string;
  _type?: string;
  _ts?: number;
  host_id?: string;
  raw_log?: string | null;
  severity?: string;
  timestamp?: string;
}

interface LogLine {
  id: string;
  rawLog: string;
  severity: string;
  arrivedAt?: number;
}

interface Props {
  hostId: string;
  hostName: string;
  running: boolean;
}

function toLine(item: { id?: string; raw_log?: string | null; severity?: string; _ts?: number }): LogLine | null {
  if (!item.id || !item.raw_log) return null;
  return {
    id: item.id,
    rawLog: item.raw_log,
    severity: item.severity || "info",
    arrivedAt: item._ts,
  };
}

/**
 * Syslog-style tail for the lab host.
 *
 * Real agent telemetry and simulated attack events share the same
 * `security_feed` channel, so this reads exactly like watching the box's
 * /var/log/auth.log while the attack plays out.
 */
export function RawLogTail({ hostId, hostName, running }: Props) {
  const { subscribe, getSnapshot } = useSecurityFeedStore(200);
  const feed = useFeedItems(subscribe, getSnapshot) as FeedItem[];
  const [flashIds, setFlashIds] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const prevCountRef = useRef(0);

  const { data } = useQuery({
    queryKey: ["events", "raw-tail", hostId],
    queryFn: () =>
      api<EventListResponse>(
        `/api/v1/events?host_id=${encodeURIComponent(hostId)}` +
          `&page_size=${SEED_LIMIT}&include_simulated=true&sort=newest`,
      ),
    enabled: Boolean(hostId),
    staleTime: 30_000,
  });

  const liveLines = useMemo(() => {
    const out: LogLine[] = [];
    for (const item of feed) {
      if (item._type !== "security_feed" || item.host_id !== hostId) continue;
      const line = toLine(item);
      if (line) out.push(line);
    }
    return out.reverse(); // oldest → newest
  }, [feed, hostId]);

  const lines = useMemo(() => {
    const seed = [...(data?.items ?? [])].reverse().map(toLine).filter(Boolean) as LogLine[];
    const seen = new Set<string>();
    const merged: LogLine[] = [];
    for (const line of [...seed, ...liveLines]) {
      if (seen.has(line.id)) continue;
      seen.add(line.id);
      merged.push(line);
    }
    return merged.slice(-MAX_LINES);
  }, [liveLines, data]);

  // Track which lines just arrived so they can flash briefly.
  useEffect(() => {
    const fresh = new Set<string>();
    for (const line of lines) {
      if (line.arrivedAt && Date.now() - line.arrivedAt < 3_000) fresh.add(line.id);
    }
    setFlashIds(fresh);
  }, [lines]);

  // Pin the tail to the newest line as it grows.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || lines.length === prevCountRef.current) return;
    prevCountRef.current = lines.length;
    el.scrollTop = el.scrollHeight;
  }, [lines.length]);

  return (
    <GlassPanel className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 mb-3">
        <h2 className="text-subheading flex items-center gap-2">
          <Radio className={cn("w-4 h-4", running ? "text-[var(--accent)] animate-pulse" : "text-[var(--muted)]")} />
          Raw syslog tail
        </h2>
        <p className="text-xs text-muted truncate">
          {hostName}
          {running && <span className="ms-2 text-[var(--accent)]">streaming</span>}
        </p>
      </div>

      <div
        ref={scrollRef}
        className="max-h-72 overflow-y-auto rounded-md border border-[var(--border-subtle)] bg-[var(--sidebar-hover)]/60 p-3"
        role="log"
        aria-label={`Raw syslog tail for ${hostName}`}
        aria-live={running ? "polite" : "off"}
      >
        {lines.length === 0 ? (
          <p className="font-mono text-xs text-[var(--muted)]">
            {running
              ? `waiting for telemetry from ${hostName}…`
              : `no recent telemetry for ${hostName} — run a scenario or wait for the agent`}
          </p>
        ) : (
          <div className="font-mono text-[11px] leading-5">
            {lines.map((line) => (
              <div
                key={line.id}
                className={cn(
                  "whitespace-pre-wrap break-all",
                  SEVERITY_TEXT[line.severity] ?? "text-[var(--muted)]",
                  flashIds.has(line.id) && "feed-row-new",
                )}
              >
                {line.rawLog}
              </div>
            ))}
            {running && (
              <span
                className="inline-block w-2 h-3 align-middle bg-[var(--accent)] animate-pulse"
                aria-hidden
              />
            )}
          </div>
        )}
      </div>
    </GlassPanel>
  );
}
