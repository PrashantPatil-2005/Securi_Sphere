"use client";

import { GlassPanel } from "@/components/ui/GlassPanel";
import type { Scenario } from "@/lib/types/simulation";

interface Props {
  scenario: Scenario | null;
}

function formatOffset(seconds: number): string {
  if (seconds === 0) return "T+0s";
  if (seconds < 60) return `T+${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return s > 0 ? `T+${m}m ${s}s` : `T+${m}m`;
}

export function KillChainPreview({ scenario }: Props) {
  if (!scenario) {
    return (
      <GlassPanel>
        <h2 className="text-subheading mb-2">Kill chain preview</h2>
        <p className="text-sm text-muted">Select a scenario to preview its attack chain.</p>
      </GlassPanel>
    );
  }

  return (
    <GlassPanel>
      <h2 className="text-subheading mb-4">Kill chain — {scenario.name}</h2>
      <ol className="relative space-y-0">
        {scenario.steps.map((step, i) => (
          <li key={step.order} className="flex gap-3 pb-4 last:pb-0">
            <div className="flex flex-col items-center shrink-0">
              <span className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium border border-accent bg-accent/10 text-accent">
                {step.order}
              </span>
              {i < scenario.steps.length - 1 && (
                <span className="w-px flex-1 min-h-[1rem] bg-border-subtle mt-1" />
              )}
            </div>
            <div className="flex-1 min-w-0 pt-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm">{step.event_type}</span>
                <span className="text-xs text-muted tabular-nums">{formatOffset(step.offset_seconds)}</span>
              </div>
              {step.mitre && (
                <div className="flex flex-wrap items-center gap-1.5 mt-1">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                    {step.mitre.technique_id}
                  </span>
                  <span className="text-xs text-muted">{step.mitre.tactic}</span>
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </GlassPanel>
  );
}
