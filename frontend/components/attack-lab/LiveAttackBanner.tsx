"use client";

import { useEffect, useMemo, useState } from "react";
import { useFeedItems, useSecurityFeedStore } from "@/lib/websocket";
import { EmotionBanner, ProgressSteps } from "@/components/ui/EmotionState";
import { groupByStage, stageForEvent } from "@/lib/attackChain";

const TITLE_BY_RANK = (rank: number, hostName: string) =>
  rank >= 6
    ? `IMPACT DETECTED on ${hostName}`
    : rank >= 5
      ? `PERSISTENCE CONFIRMED on ${hostName}`
      : rank >= 4
        ? `PRIVILEGE ESCALATION on ${hostName}`
        : rank >= 3
          ? `ACCESS GAINED on ${hostName}`
          : rank >= 2
            ? `ATTACK IN PROGRESS on ${hostName}`
            : `RECONNAISSANCE on ${hostName}`;

interface FeedItem {
  _type?: string;
  _ts?: number;
  host_id?: string;
  event_type?: string;
  description?: string;
  title?: string;
  severity?: string;
}

export interface LiveAttackBannerProps {
  running: boolean;
  hostId: string;
  hostName: string;
  scenarioName?: string;
  expectedEvents?: number;
  runStartedAt: number | null;
  /** Keep the banner up briefly after the run so the final stage lands. */
  dwellMs?: number;
}

export function LiveAttackBanner({
  running,
  hostId,
  hostName,
  scenarioName,
  expectedEvents,
  runStartedAt,
  dwellMs = 20_000,
}: LiveAttackBannerProps) {
  const { subscribe, getSnapshot } = useSecurityFeedStore(120);
  const feed = useFeedItems(subscribe, getSnapshot) as FeedItem[];
  const [dwellActive, setDwellActive] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (running) {
      setDwellActive(false);
      return;
    }
    if (!runStartedAt) return;
    setDwellActive(true);
    const timer = setTimeout(() => setDwellActive(false), dwellMs);
    return () => clearTimeout(timer);
  }, [running, runStartedAt, dwellMs]);

  useEffect(() => {
    if (!running || !runStartedAt) return;
    setElapsed(0);
    const tick = setInterval(
      () => setElapsed(Math.round((Date.now() - runStartedAt) / 1000)),
      500,
    );
    return () => clearInterval(tick);
  }, [running, runStartedAt]);

  const { stage, steps, eventCount, alertCount, latest } = useMemo(() => {
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

    const groups = groupByStage(runEvents, (item) => stageForEvent(item.event_type));
    const topRank = groups.at(-1)?.stage.rank ?? 0;
    const last = runEvents[0];

    return {
      stage: {
        rank: topRank,
        label: groups.at(-1)?.stage.label ?? "Injection",
      },
      steps: groups.map((g) => g.stage.label),
      eventCount: runEvents.length,
      alertCount: runAlerts.length,
      latest: last?.description || last?.event_type || "",
    };
  }, [feed, hostId, runStartedAt]);

  const visible = (running || dwellActive) && !!runStartedAt && eventCount > 0;
  if (!visible) return null;

  const tone = running ? "urgency" : alertCount > 0 ? "success" : "confidence";
  const title = TITLE_BY_RANK(stage.rank, hostName);
  const progressText = running
    ? `Stage: ${stage.label} — ${eventCount}${expectedEvents ? `/${expectedEvents}` : ""} events injected${latest ? ` · latest: ${latest}` : ""}`
    : `${eventCount} events injected · ${alertCount} alerts raised${scenarioName ? ` · ${scenarioName}` : ""}`;

  return (
    <EmotionBanner tone={tone} title={title}>
      {steps.length > 0 && (
        <div className="mt-2">
          <ProgressSteps steps={steps} currentIndex={Math.max(steps.length - 1, 0)} />
        </div>
      )}
      <p className="mt-2 text-xs text-muted">{progressText}</p>
      {running && <p className="mt-1 text-xs text-muted">{elapsed}s elapsed · streaming</p>}
    </EmotionBanner>
  );
}
