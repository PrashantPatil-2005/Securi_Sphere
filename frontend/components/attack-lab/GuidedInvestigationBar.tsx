"use client";

import Link from "next/link";
import { ArrowRight, ListOrdered } from "lucide-react";
import { buildGuidedInvestigationSteps } from "@/lib/guidedInvestigation";
import type { SimulationRunResult } from "@/lib/types/simulation";
import { cn } from "@/lib/utils/cn";

interface Props {
  result: SimulationRunResult;
}

export function GuidedInvestigationBar({ result }: Props) {
  const steps = buildGuidedInvestigationSteps(result).filter((s) => s.available);
  const nextStep = steps[0];

  if (!nextStep) return null;

  return (
    <div className="rounded-lg border border-accent/30 bg-accent/5 p-4 space-y-3">
      <div className="flex items-start gap-2">
        <ListOrdered className="w-4 h-4 text-accent shrink-0 mt-0.5" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">Guided investigation</p>
          <p className="text-xs text-muted mt-0.5">{nextStep.hint}</p>
        </div>
        <Link href={nextStep.href} className="btn-primary text-xs shrink-0 inline-flex items-center gap-1">
          {nextStep.label}
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      <ol className="flex flex-wrap gap-2">
        {steps.map((step, index) => (
          <li key={step.id}>
            <Link
              href={step.href}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors",
                index === 0
                  ? "border-accent/40 bg-accent/10 text-accent"
                  : "border-border-subtle text-muted hover:text-foreground hover:bg-[var(--sidebar-hover)]",
              )}
            >
              <span className="tabular-nums opacity-70">{index + 1}</span>
              {step.label}
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
