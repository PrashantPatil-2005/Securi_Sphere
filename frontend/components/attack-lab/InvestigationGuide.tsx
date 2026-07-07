"use client";

import Link from "next/link";
import { CheckCircle2, Circle } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { useOnboardingProgress } from "@/lib/hooks/useOnboardingProgress";
import { cn } from "@/lib/utils/cn";

const GUIDE_STEPS = [
  {
    id: "alerts",
    label: "Review alerts — detection rules should fire",
    href: "/alerts",
    hint: "Open investigation pane and start triage",
    isComplete: (p: { triagedAlerts: number; offenses: number }) => p.triagedAlerts >= 1 || p.offenses >= 1,
  },
  {
    id: "offenses",
    label: "Check offenses — correlated activity grouped",
    href: "/offenses",
    hint: "Promote to incident when ready",
    isComplete: (p: { offenses: number }) => p.offenses >= 1,
  },
  {
    id: "workspace",
    label: "Open Case Workspace — unified investigation view",
    href: "/investigation",
    hint: "Alert, offense, host, and events in one pane",
    isComplete: (p: { incidents: number; offenses: number }) => p.incidents >= 1 || p.offenses >= 1,
  },
  {
    id: "search",
    label: "SIEM search — try event_type:network_flow",
    href: "/search",
    hint: "Or search source_ip:10.0.0.50 for C2 pattern",
    isComplete: (p: { searchCompleted: boolean }) => p.searchCompleted,
  },
  {
    id: "timeline",
    label: "Attack timeline — reconstructed kill chain",
    href: "/timeline",
    hint: "Review MITRE technique chips and confidence",
    isComplete: (p: { simulationRuns: number; offenses: number }) => p.simulationRuns >= 1 && p.offenses >= 1,
  },
  {
    id: "mitre",
    label: "MITRE ATT&CK — coverage heatmap",
    href: "/mitre",
    hint: "Map techniques from simulated events",
    isComplete: (p: { offenses: number }) => p.offenses >= 1,
  },
  {
    id: "incidents",
    label: "Incidents — formal investigation record",
    href: "/incidents",
    hint: "After promoting an offense to incident",
    isComplete: (p: { incidents: number }) => p.incidents >= 1,
  },
];

export function InvestigationGuide() {
  const { progress } = useOnboardingProgress();

  const completed = GUIDE_STEPS.filter((s) => s.isComplete(progress)).length;

  return (
    <GlassPanel>
      <div className="flex items-center justify-between gap-2 mb-4">
        <h2 className="text-subheading">SOC investigation guide</h2>
        <span className="text-xs text-muted tabular-nums">
          {completed}/{GUIDE_STEPS.length}
        </span>
      </div>
      <p className="text-sm text-muted mb-4">
        Follow this checklist after running a simulation. Steps complete automatically as you work through the platform.
      </p>
      <ul className="space-y-1">
        {GUIDE_STEPS.map((step) => {
          const done = step.isComplete(progress);
          return (
            <li key={step.id}>
              <div className="flex items-start gap-2 p-2 rounded-lg hover:bg-[var(--sidebar-hover)] transition-colors group">
                {done ? (
                  <CheckCircle2 className="w-4 h-4 text-success shrink-0 mt-0.5" />
                ) : (
                  <Circle className="w-4 h-4 text-muted shrink-0 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <Link
                    href={step.href}
                    className={cn("text-sm block", done && "text-muted line-through")}
                  >
                    {step.label}
                  </Link>
                  <p className="text-xs text-muted mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {step.hint}
                  </p>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </GlassPanel>
  );
}
