"use client";

import { CheckCircle2, Circle } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { EmotionTone } from "@/components/ui/EmotionState";

export type TriageStep = "review" | "investigate" | "classify" | "resolve";

const STEPS: { id: TriageStep; label: string }[] = [
  { id: "review", label: "Review context" },
  { id: "investigate", label: "Investigate" },
  { id: "classify", label: "Classify" },
  { id: "resolve", label: "Resolve" },
];

function resolveStep(status: string, hasFeedback: boolean): TriageStep {
  if (status === "resolved") return "resolve";
  if (hasFeedback) return "classify";
  if (status === "investigating") return "investigate";
  return "review";
}

export function TriageStepper({
  status,
  severity,
  hasFeedback,
}: {
  status: string;
  severity: string;
  hasFeedback: boolean;
}) {
  const current = resolveStep(status, hasFeedback);
  const currentIndex = STEPS.findIndex((s) => s.id === current);
  const tone: EmotionTone =
    severity === "critical" ? "urgency" : severity === "high" ? "progress" : "calm";

  return (
    <div className={cn("rounded-lg border p-3", `emotion-${tone}`)}>
      <p className="text-xs font-medium text-muted mb-2 uppercase tracking-wide">Triage flow</p>
      <ol className="flex flex-wrap gap-2">
        {STEPS.map((step, i) => {
          const done = i < currentIndex;
          const active = i === currentIndex;
          return (
            <li
              key={step.id}
              className={cn(
                "flex items-center gap-1.5 text-xs px-2 py-1 rounded-md border",
                done && "border-success/30 text-success",
                active && "border-accent/40 text-foreground font-medium",
                !done && !active && "border-border-subtle text-muted",
              )}
            >
              {done ? <CheckCircle2 className="w-3 h-3" /> : <Circle className="w-3 h-3" />}
              {step.label}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
