"use client";

import { memo } from "react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";
import { EmptyState } from "@/components/design-system/EmptyState";
import type { TimelineEvent } from "@/lib/types/timeline";

interface TimelineReplayProps {
  events: TimelineEvent[];
  title: string;
  currentIndex: number;
  onIndexChange: (index: number) => void;
  playing: boolean;
  onTogglePlay: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
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

const SPEEDS = [0.5, 1, 2, 4];

function TimelineReplayInner({
  events,
  title,
  currentIndex,
  onIndexChange,
  playing,
  onTogglePlay,
  speed,
  onSpeedChange,
  isLoading,
}: TimelineReplayProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Replay" subtitle="Loading events..." />
        <div className="p-4 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex gap-3">
              <div className="h-3 w-16 skeleton rounded" />
              <div className="h-3 flex-1 skeleton rounded" />
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (events.length === 0) {
    return (
      <Card>
        <CardHeader title="Replay" />
        <EmptyState
          title="No events"
          description="No events available for replay in this timeline."
        />
      </Card>
    );
  }

  const progress = events.length <= 1 ? 100 : Math.round((currentIndex / (events.length - 1)) * 100);

  return (
    <Card>
      <CardHeader
        title="Replay"
        subtitle={`Replaying ${title}`}
      />
      <div className="p-4 space-y-4">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-border-subtle bg-card-elevated">
          <button
            type="button"
            onClick={() => onIndexChange(0)}
            disabled={currentIndex === 0}
            className="p-1.5 rounded hover:bg-[var(--sidebar-hover)] disabled:opacity-30 transition-colors"
            aria-label="Restart"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          </button>
          <button
            type="button"
            onClick={onTogglePlay}
            className="p-1.5 rounded bg-accent text-accent-foreground hover:bg-accent-muted transition-colors"
            aria-label={playing ? "Pause" : "Play"}
          >
            {playing ? (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
            )}
          </button>
          <button
            type="button"
            onClick={() => { onTogglePlay(); onIndexChange(Math.min(currentIndex + 1, events.length - 1)); }}
            disabled={currentIndex >= events.length - 1}
            className="p-1.5 rounded hover:bg-[var(--sidebar-hover)] disabled:opacity-30 transition-colors"
            aria-label="Next"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
          <div className="flex items-center gap-1 ml-auto">
            {SPEEDS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSpeedChange(s)}
                className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
                  speed === s ? "bg-accent/15 text-accent" : "text-muted hover:text-foreground"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Progress */}
        <div className="space-y-1">
          <div className="flex justify-between text-[10px] text-muted tabular-nums">
            <span>Step {currentIndex + 1} / {events.length}</span>
            <span>{progress}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={Math.max(events.length - 1, 0)}
            value={currentIndex}
            onChange={(e) => onIndexChange(Number(e.target.value))}
            className="w-full accent-[var(--accent)]"
            aria-label="Replay scrubber"
          />
        </div>

        {/* Event list */}
        <div className="relative pl-6 space-y-0 max-h-[400px] overflow-y-auto">
          {events.map((e, i) => {
            const active = i === currentIndex;
            const revealed = i <= currentIndex;
            return (
              <div
                key={e.id}
                className={`relative pb-4 last:pb-0 transition-opacity duration-300 ${
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
                    <span className="text-[10px] text-muted tabular-nums font-mono">
                      {formatTime(e.timestamp)}
                    </span>
                    <SeverityBadge severity={e.severity} />
                    {e.mitre_technique_id && (
                      <span className="text-[9px] font-mono text-accent">{e.mitre_technique_id}</span>
                    )}
                  </div>
                  <p className="font-medium text-xs mt-0.5 font-mono">{e.event_type}</p>
                  {e.description && (
                    <p className="text-[11px] text-muted mt-0.5">{e.description}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

export const TimelineReplay = memo(TimelineReplayInner);
