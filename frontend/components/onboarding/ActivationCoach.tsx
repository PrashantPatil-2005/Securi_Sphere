"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowRight, X } from "lucide-react";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { useUxEnabled } from "@/lib/featureFlags";
import { useOnboardingProgress } from "@/lib/hooks/useOnboardingProgress";
import { track } from "@/lib/telemetry";

const COACH_DISMISSED_KEY = "securi_activation_coach_dismissed";

interface CoachTip {
  id: string;
  tone: "calm" | "confidence" | "urgency" | "success" | "progress";
  title: string;
  message: string;
  href: string;
  cta: string;
  paths?: string[];
}

export function ActivationCoach() {
  const enabled = useUxEnabled("ux_activation_coach_enabled");
  const pathname = usePathname();
  const { steps, progress, completedCount, totalSteps } = useOnboardingProgress();
  const [dismissedId, setDismissedId] = useState<string | null>(null);

  const tip = useMemo((): CoachTip | null => {
    if (!enabled || completedCount >= totalSteps) return null;

    const next = steps.find((s) => !s.isComplete(progress));
    if (!next) return null;

    const tips: Record<string, CoachTip> = {
      host: {
        id: "coach-host",
        tone: "calm",
        title: "Start with a host or jump to Attack Lab",
        message: "Add a Linux agent for live telemetry, or skip straight to simulation for a fast demo.",
        href: "/hosts",
        cta: "Set up hosts",
        paths: ["/", "/hosts"],
      },
      simulation: {
        id: "coach-simulation",
        tone: "progress",
        title: "Your next win: run Attack Lab",
        message: "A guided simulation creates realistic alerts and offenses in under a minute.",
        href: "/simulation",
        cta: "Open Attack Lab",
        paths: ["/", "/simulation", "/hosts"],
      },
      triage: {
        id: "coach-triage",
        tone: "urgency",
        title: "Alerts are waiting — start triage",
        message: "Open an alert, investigate context, and mark your first resolution.",
        href: "/alerts",
        cta: "Triage alerts",
        paths: ["/", "/alerts", "/simulation"],
      },
      offense: {
        id: "coach-offense",
        tone: "confidence",
        title: "Promote an offense to incident",
        message: "Complete the golden path by turning correlated activity into a tracked incident.",
        href: "/offenses",
        cta: "Review offenses",
        paths: ["/offenses", "/alerts"],
      },
      search: {
        id: "coach-search",
        tone: "calm",
        title: "Run your first SIEM search",
        message: "Query events across hosts to validate detection coverage.",
        href: "/search",
        cta: "Open search",
        paths: ["/", "/search"],
      },
      notifications: {
        id: "coach-notifications",
        tone: "success",
        title: "Wire up notifications",
        message: "Enable Slack, email, or Telegram so your team gets alerted outside the console.",
        href: "/settings",
        cta: "Configure alerts",
        paths: ["/settings", "/"],
      },
    };

    const candidate = tips[next.id];
    if (!candidate) return null;
    if (candidate.paths && !candidate.paths.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
      return null;
    }
    return candidate;
  }, [enabled, steps, progress, completedCount, totalSteps, pathname]);

  useEffect(() => {
    if (tip) track("activation_coach_shown", { tip_id: tip.id, path: pathname });
  }, [tip, pathname]);

  if (!tip) return null;
  if (dismissedId === tip.id) return null;
  if (typeof window !== "undefined" && sessionStorage.getItem(COACH_DISMISSED_KEY) === tip.id) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-30 max-w-sm animate-in fade-in slide-in-from-bottom-2">
      <EmotionBanner
        tone={tip.tone}
        title={tip.title}
        message={tip.message}
        action={
          <div className="flex items-center gap-1 shrink-0">
            <Link
              href={tip.href}
              className="btn-primary text-xs py-1.5 px-2.5 inline-flex items-center gap-1"
              onClick={() => track("activation_coach_action", { tip_id: tip.id, action: "cta" })}
            >
              {tip.cta}
              <ArrowRight className="w-3 h-3" />
            </Link>
            <button
              type="button"
              className="btn-ghost p-1.5"
              aria-label="Dismiss coach"
              onClick={() => {
                sessionStorage.setItem(COACH_DISMISSED_KEY, tip.id);
                setDismissedId(tip.id);
                track("activation_coach_action", { tip_id: tip.id, action: "dismiss" });
              }}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        }
      />
    </div>
  );
}
