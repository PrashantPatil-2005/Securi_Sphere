"use client";

import { useEffect, useMemo, useState } from "react";
import { EmotionBanner, ProgressSteps } from "@/components/ui/EmotionState";
import { useFeedItems, useSecurityFeedStore } from "@/lib/websocket";
import { track } from "@/lib/telemetry";

/**
 * Pipeline stages, matching what `execute_simulation_run` actually does.
 * Events are detected as they land, so the run spends its first phase
 * injecting and its tail correlating + building timelines.
 */
const STAGES = ["Injecting events", "Correlating offenses", "Building timelines"];

interface FeedItem {
  _type?: string;
  _ts?: number;
  host_id?: string;
  event_type?: string;
  description?: string;
  title?: string;
}

export interface SimulationLiveProgressProps {
  running: boolean;
  scenarioName?: string;
  hostId: string;
  expectedEvents?: number;
  runStartedAt: number | null;
}

export function SimulationLiveProgress({
  running,
  scenarioName,
  hostId,
  expectedEvents,
  runStartedAt,
}: SimulationLiveProgressProps) {
  const { subscribe, getSnapshot } = useSecurityFeedStore(120);
  const feed = useFeedItems(subscribe, getSnapshot) as FeedItem[];
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!running || !runStartedAt) return;
    track("simulation_started", { scenario: scenarioName });
    setElapsed(0);
    const tick = setInterval(
      () => setElapsed(Math.round((Date.now() - runStartedAt) / 1000)),
      500,
    );
    return () => clearInterval(tick);
  }, [running, runStartedAt, scenarioName]);

  const { seen, alertCount, latest } = useMemo(() => {
    const windowStart = runStartedAt ?? 0;
    const runEvents = feed.filter(
      (item) =>
        item._type === "security_feed" &&
        item.host_id === hostId &&
        (item._ts ?? 0) >= windowStart,
    );
    const runAlerts = feed.filter(
      (item) => item._type === "new_alert" && (item._ts ?? 0) >= windowStart,
    );
    return {
      seen: runEvents.length,
      alertCount: runAlerts.length,
      latest: runEvents[0]?.description || runEvents[0]?.event_type || "",
    };
  }, [feed, hostId, runStartedAt]);

  if (!running) return null;

  const done = expectedEvents ? seen >= expectedEvents : false;
  const stageIndex = done ? 1 : 0;
  const denominator = expectedEvents ? `/${expectedEvents}` : "";

  return (
    <div className="space-y-3">
      <EmotionBanner
        tone="progress"
        title={scenarioName ? `Attack unfolding live — ${scenarioName}` : "Attack unfolding live"}
        message={
          `${seen}${denominator} events injected · ${alertCount} alerts · ${elapsed}s elapsed` +
          (latest ? ` · latest: ${latest}` : "")
        }
      />
      <ProgressSteps steps={STAGES} currentIndex={stageIndex} />
    </div>
  );
}
