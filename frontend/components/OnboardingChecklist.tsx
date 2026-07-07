"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Circle, ListChecks } from "lucide-react";
import { Panel } from "@/components/ui/Panel";
import { ONBOARDING_DISMISSED_KEY } from "@/lib/onboarding";
import { useOnboardingProgress } from "@/lib/hooks/useOnboardingProgress";

export function OnboardingChecklist() {
  const [dismissed, setDismissed] = useState(true);
  const { steps, progress, completedCount, totalSteps } = useOnboardingProgress();

  useEffect(() => {
    setDismissed(localStorage.getItem(ONBOARDING_DISMISSED_KEY) === "1");
  }, []);

  if (dismissed || completedCount >= totalSteps) return null;

  return (
    <Panel
      title="Getting started"
      subtitle={`${completedCount}/${totalSteps} complete — SOC lab walkthrough (no agent required for simulation)`}
      action={
        <button
          type="button"
          className="btn-ghost text-xs"
          onClick={() => {
            localStorage.setItem(ONBOARDING_DISMISSED_KEY, "1");
            setDismissed(true);
          }}
        >
          Dismiss
        </button>
      }
    >
      <ul className="space-y-2">
        {steps.map((step) => {
          const done = step.isComplete(progress);
          return (
            <li key={step.id}>
              <Link
                href={step.href}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--sidebar-hover)] transition-colors"
              >
                {done ? (
                  <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-muted shrink-0" />
                )}
                <span className={done ? "text-muted line-through text-sm" : "text-sm"}>
                  {step.label}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
      <p className="text-caption normal-case text-muted mt-3 flex items-center gap-1.5">
        <ListChecks className="w-3.5 h-3.5" />
        Tip: press Ctrl+K for quick navigation · simulation-only demo needs no Ubuntu VM
      </p>
    </Panel>
  );
}
