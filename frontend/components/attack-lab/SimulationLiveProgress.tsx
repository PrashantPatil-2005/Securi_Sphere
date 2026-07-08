"use client";

import { useEffect, useState } from "react";
import { EmotionBanner, ProgressSteps } from "@/components/ui/EmotionState";
import { useUxEnabled } from "@/lib/featureFlags";
import { track } from "@/lib/telemetry";

const STAGES = [
  "Preparing scenario",
  "Injecting events",
  "Running detection rules",
  "Correlating offenses",
  "Building timelines",
];

interface Props {
  running: boolean;
  scenarioName?: string;
}

export function SimulationLiveProgress({ running, scenarioName }: Props) {
  const enabled = useUxEnabled("ux_live_simulation_enabled");
  const [stageIndex, setStageIndex] = useState(0);

  useEffect(() => {
    if (!running || !enabled) {
      setStageIndex(0);
      return;
    }

    track("simulation_started", { scenario: scenarioName });
    setStageIndex(0);

    const timers = STAGES.map((_, i) =>
      setTimeout(() => {
        setStageIndex(i);
        track("simulation_stage", { stage: STAGES[i], index: i });
      }, i * 900),
    );

    return () => timers.forEach(clearTimeout);
  }, [running, enabled, scenarioName]);

  if (!enabled || !running) return null;

  return (
    <div className="space-y-3">
      <EmotionBanner
        tone="progress"
        title="Attack unfolding live"
        message={
          scenarioName
            ? `Running ${scenarioName} — watch the security feed for real-time events.`
            : "Simulated attack stages are executing across the pipeline."
        }
      />
      <ProgressSteps steps={STAGES} currentIndex={stageIndex} />
    </div>
  );
}
