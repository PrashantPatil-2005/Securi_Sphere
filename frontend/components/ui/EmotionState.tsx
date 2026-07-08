"use client";

import { memo, type ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, Loader2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { useTheme } from "@/lib/theme/ThemeProvider";

export type EmotionTone = "calm" | "confidence" | "urgency" | "success" | "progress";

const TONE_CLASS: Record<EmotionTone, string> = {
  calm: "emotion-calm",
  confidence: "emotion-confidence",
  urgency: "emotion-urgency",
  success: "emotion-success",
  progress: "emotion-progress",
};

const TONE_ICON: Record<EmotionTone, ReactNode> = {
  calm: <Info className="w-4 h-4 shrink-0" />,
  confidence: <Sparkles className="w-4 h-4 shrink-0" />,
  urgency: <AlertCircle className="w-4 h-4 shrink-0" />,
  success: <CheckCircle2 className="w-4 h-4 shrink-0" />,
  progress: <Loader2 className="w-4 h-4 shrink-0 animate-spin" />,
};

export const EmotionBanner = memo(function EmotionBanner({
  tone = "calm",
  title,
  message,
  action,
  className,
}: {
  tone?: EmotionTone;
  title: string;
  message?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("emotion-banner", TONE_CLASS[tone], className)} role="status">
      <div className="flex items-start gap-3">
        <span className="emotion-banner-icon" aria-hidden>
          {TONE_ICON[tone]}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground">{title}</p>
          {message && <p className="text-xs text-muted mt-0.5">{message}</p>}
        </div>
        {action}
      </div>
    </div>
  );
});

export const ProgressSteps = memo(function ProgressSteps({
  steps,
  currentIndex,
}: {
  steps: string[];
  currentIndex: number;
}) {
  const { reducedMotion } = useTheme();
  return (
    <ol className="progress-steps" aria-label="Progress">
      {steps.map((label, i) => {
        const done = i < currentIndex;
        const active = i === currentIndex;
        return (
          <li
            key={label}
            className={cn(
              "progress-step",
              done && "progress-step-done",
              active && !reducedMotion && "progress-step-active",
            )}
          >
            <span className="progress-step-dot" aria-hidden />
            <span className="text-xs">{label}</span>
          </li>
        );
      })}
    </ol>
  );
});

export const VitalityPulse = memo(function VitalityPulse({
  active,
  className,
}: {
  active?: boolean;
  className?: string;
}) {
  const { reducedMotion } = useTheme();
  if (!active || reducedMotion) return null;
  return <span className={cn("vitality-pulse", className)} aria-hidden />;
});
