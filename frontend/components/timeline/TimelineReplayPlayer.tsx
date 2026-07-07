"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import { REPLAY_SPEEDS, replayProgress, replayStepDelayMs, type ReplaySpeed } from "@/lib/timelineReplay";
import { Button } from "@/components/ui/Button";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { cn } from "@/lib/utils/cn";

export interface TimelineReplayEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  mitre_technique_id: string | null;
  timestamp: string;
}

interface TimelineReplayPlayerProps {
  events: TimelineReplayEvent[];
  title?: string;
}

export function TimelineReplayPlayer({ events, title }: TimelineReplayPlayerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<ReplaySpeed>(1);
  const stepRefs = useRef<(HTMLDivElement | null)[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const goTo = useCallback(
    (index: number) => {
      if (!events.length) return;
      const next = Math.max(0, Math.min(index, events.length - 1));
      setCurrentIndex(next);
    },
    [events.length],
  );

  useEffect(() => {
    setCurrentIndex(0);
    setPlaying(false);
    clearTimer();
  }, [events, clearTimer]);

  useEffect(() => {
    const el = stepRefs.current[currentIndex];
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [currentIndex]);

  useEffect(() => {
    clearTimer();
    if (!playing || events.length <= 1) return;

    if (currentIndex >= events.length - 1) {
      setPlaying(false);
      return;
    }

    const delay = replayStepDelayMs(events[currentIndex].timestamp, events[currentIndex + 1].timestamp, speed);
    timerRef.current = setTimeout(() => {
      setCurrentIndex((i) => i + 1);
    }, delay);

    return clearTimer;
  }, [playing, currentIndex, events, speed, clearTimer]);

  useEffect(() => () => clearTimer(), [clearTimer]);

  if (!events.length) {
    return <p className="text-sm text-muted">No events in this timeline.</p>;
  }

  const progress = replayProgress(currentIndex, events.length);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2 p-3 rounded-lg border border-border-subtle bg-glass/40">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => goTo(0)}
          disabled={currentIndex === 0}
          aria-label="Restart"
        >
          <SkipBack className="w-4 h-4" />
        </Button>
        <Button
          type="button"
          size="sm"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? "Pause replay" : "Play replay"}
        >
          {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {playing ? "Pause" : "Play"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => {
            setPlaying(false);
            goTo(currentIndex + 1);
          }}
          disabled={currentIndex >= events.length - 1}
          aria-label="Next step"
        >
          <SkipForward className="w-4 h-4" />
        </Button>

        <div className="flex items-center gap-1 ml-auto">
          {REPLAY_SPEEDS.map((s) => (
            <Button
              key={s}
              type="button"
              variant="ghost"
              size="sm"
              className={cn(speed === s && "bg-accent/10 text-accent border-accent/30")}
              onClick={() => setSpeed(s)}
            >
              {s}x
            </Button>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-xs text-muted tabular-nums">
          <span>
            Step {currentIndex + 1} / {events.length}
          </span>
          <span>{progress}%</span>
        </div>
        <input
          type="range"
          min={0}
          max={Math.max(events.length - 1, 0)}
          value={currentIndex}
          onChange={(e) => {
            setPlaying(false);
            goTo(Number(e.target.value));
          }}
          className="w-full accent-[var(--accent)]"
          aria-label="Replay scrubber"
        />
      </div>

      {title && (
        <p className="text-xs text-muted">
          Replaying <span className="text-foreground font-medium">{title}</span> in chronological order
        </p>
      )}

      <div className="relative pl-6 space-y-0 max-h-[480px] overflow-y-auto pr-1">
        {events.map((e, i) => {
          const active = i === currentIndex;
          const revealed = i <= currentIndex;
          return (
            <div
              key={e.id}
              ref={(el) => {
                stepRefs.current[i] = el;
              }}
              className={cn(
                "relative pb-6 last:pb-0 transition-opacity duration-300",
                !revealed && "opacity-35",
              )}
            >
              {i < events.length - 1 && (
                <div
                  className={cn(
                    "absolute left-[5px] top-3 bottom-0 w-px",
                    i < currentIndex ? "bg-accent/50" : "bg-border-subtle",
                  )}
                />
              )}
              <div
                className={cn(
                  "absolute left-0 top-1.5 w-2.5 h-2.5 rounded-full ring-4 transition-all duration-300",
                  active
                    ? "bg-accent ring-accent/30 scale-125"
                    : i < currentIndex
                      ? "bg-accent/80 ring-accent/15"
                      : "bg-border-subtle ring-transparent",
                )}
              />
              <div
                className={cn(
                  "ml-4 rounded-lg p-3 border transition-colors",
                  active ? "border-accent/40 bg-accent/5" : "border-transparent",
                )}
              >
                <p className="text-xs text-muted tabular-nums">{new Date(e.timestamp).toLocaleString()}</p>
                <p className="font-medium mt-0.5">{e.event_type}</p>
                {e.description && <p className="text-sm text-muted mt-0.5">{e.description}</p>}
                <div className="flex items-center gap-2 mt-1">
                  <SeverityBadge severity={e.severity} />
                  {e.mitre_technique_id && (
                    <span className="text-[10px] font-mono text-accent">{e.mitre_technique_id}</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
