"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CheckCircle2, Circle, Rocket } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import {
  dismissOnboardingWizard,
  isOnboardingWizardDismissed,
  reopenOnboardingWizard,
} from "@/lib/onboarding";
import { useOnboardingProgress } from "@/lib/hooks/useOnboardingProgress";

const STEP_HINTS: Record<string, string> = {
  host: "Register a Linux agent, or skip this step and use Attack Lab simulation only.",
  simulation: "Run the multi-stage attack scenario to generate realistic alerts and offenses.",
  triage: "Open an alert, start investigation, or resolve it from the investigation pane.",
  offense: "Open an offense and promote it to an incident from the offense detail panel.",
  search: "Run any SIEM query or saved search — completion is tracked automatically.",
  notifications: "Enable email, Slack, or Telegram delivery in Settings → Notifications.",
};

export function OnboardingWizard() {
  const pathname = usePathname();
  const { steps, progress, completedCount, totalSteps } = useOnboardingProgress();
  const [open, setOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);

  const wizardSteps = useMemo(
    () => [{ id: "welcome", label: "Welcome to Securi", href: "/" }, ...steps],
    [steps],
  );

  const evaluateOpen = useCallback(() => {
    if (isOnboardingWizardDismissed() || completedCount >= totalSteps) {
      setOpen(false);
      return;
    }
    setOpen(true);
  }, [completedCount, totalSteps]);

  useEffect(() => {
    evaluateOpen();
    const onReopen = () => {
      setStepIndex(0);
      setOpen(true);
    };
    window.addEventListener("securi-onboarding-wizard-open", onReopen);
    return () => window.removeEventListener("securi-onboarding-wizard-open", onReopen);
  }, [evaluateOpen]);

  useEffect(() => {
    if (!open) return;
    if (completedCount >= totalSteps) {
      dismissOnboardingWizard();
      setOpen(false);
    }
  }, [open, completedCount, totalSteps]);

  const current = wizardSteps[stepIndex];
  const isWelcome = current?.id === "welcome";
  const stepComplete =
    !isWelcome && current && "isComplete" in current ? current.isComplete(progress) : false;
  const progressPct = Math.round((completedCount / Math.max(totalSteps, 1)) * 100);

  function closeWizard() {
    dismissOnboardingWizard();
    setOpen(false);
  }

  if (!current) return null;

  return (
    <Dialog
      open={open}
      onClose={closeWizard}
      title={isWelcome ? "Welcome to Securi" : current.label}
      description={
        isWelcome
          ? "A short guided tour to your first SOC investigation — about 10 minutes."
          : STEP_HINTS[current.id] ?? "Complete this step to finish onboarding."
      }
      size="lg"
    >
      <div className="space-y-5">
        <div>
          <div className="flex justify-between text-xs text-muted mb-1">
            <span>
              Progress {completedCount}/{totalSteps}
            </span>
            <span>{progressPct}%</span>
          </div>
          <div className="h-2 rounded-full bg-[var(--sidebar-hover)] overflow-hidden">
            <div className="h-full bg-accent transition-all" style={{ width: `${progressPct}%` }} />
          </div>
        </div>

        {isWelcome ? (
          <div className="rounded-lg border border-border-subtle p-4 space-y-2 text-sm text-muted">
            <p className="flex items-center gap-2 text-foreground font-medium">
              <Rocket className="w-4 h-4 text-accent" />
              What you will set up
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Generate demo security events (Attack Lab)</li>
              <li>Triage alerts and review offenses</li>
              <li>Promote an offense to an incident</li>
              <li>Run SIEM search and configure notifications</li>
            </ul>
          </div>
        ) : (
          <div className="rounded-lg border border-border-subtle p-4">
            <div className="flex items-center gap-2 mb-2">
              {stepComplete ? (
                <CheckCircle2 className="w-5 h-5 text-success" />
              ) : (
                <Circle className="w-5 h-5 text-muted" />
              )}
              <span className="text-sm font-medium">{stepComplete ? "Completed" : "Pending"}</span>
            </div>
            <p className="text-sm text-muted">{STEP_HINTS[current.id]}</p>
            {current.href !== pathname && (
              <Link href={current.href} className="btn-primary text-sm inline-flex mt-3" onClick={() => setOpen(false)}>
                Go to this step
              </Link>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={stepIndex === 0}
              onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
            >
              Back
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={stepIndex >= wizardSteps.length - 1}
              onClick={() => setStepIndex((i) => Math.min(wizardSteps.length - 1, i + 1))}
            >
              Next
            </Button>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={closeWizard}>
              Skip tour
            </Button>
            {stepIndex >= wizardSteps.length - 1 && completedCount >= totalSteps ? (
              <Button type="button" size="sm" onClick={closeWizard}>
                Finish
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </Dialog>
  );
}

export function OnboardingWizardTrigger() {
  return (
    <button
      type="button"
      className="btn-ghost text-xs"
      onClick={() => reopenOnboardingWizard()}
    >
      Open setup wizard
    </button>
  );
}
