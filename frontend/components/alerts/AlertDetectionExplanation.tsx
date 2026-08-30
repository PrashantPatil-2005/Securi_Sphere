"use client";

import { memo } from "react";
import { FileCode2, Crosshair, ThumbsUp, ThumbsDown } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Card, CardHeader } from "@/components/design-system";
import type { Alert } from "@/lib/types/alert";

interface AlertDetectionExplanationProps {
  alert: Alert;
  rule?: {
    name: string;
    rule_type: string;
    threshold: number | null;
    window_minutes: number | null;
    severity: string;
    false_positive_count: number;
    true_positive_count: number;
  } | null;
}

function ConfidenceBar({ value }: { value: number }) {
  const clamped = Math.min(100, Math.max(0, value));
  let barColor = "bg-success";
  if (clamped < 40) barColor = "bg-muted";
  else if (clamped < 70) barColor = "bg-warning";
  else if (clamped < 90) barColor = "bg-accent";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted">Confidence</span>
        <span className="text-xs font-semibold tabular-nums text-foreground">{clamped}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-card-elevated overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", barColor)}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

function RuleFeedbackStats({
  falsePositiveCount,
  truePositiveCount,
}: {
  falsePositiveCount: number;
  truePositiveCount: number;
}) {
  const total = falsePositiveCount + truePositiveCount;
  if (total === 0) return null;

  return (
    <div className="flex items-center gap-4 text-xs text-muted">
      <div className="flex items-center gap-1.5">
        <ThumbsUp className="w-3 h-3 text-success" />
        <span className="tabular-nums">{truePositiveCount}</span>
        <span>true positive{truePositiveCount !== 1 ? "s" : ""}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <ThumbsDown className="w-3 h-3 text-danger" />
        <span className="tabular-nums">{falsePositiveCount}</span>
        <span>false positive{falsePositiveCount !== 1 ? "s" : ""}</span>
      </div>
    </div>
  );
}

function AlertDetectionExplanationInner({
  alert,
  rule,
}: AlertDetectionExplanationProps) {
  return (
    <Card>
      <CardHeader title="Detection Explanation" />
      <div className="p-4 space-y-4">
        {rule ? (
          <>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <FileCode2 className="w-3.5 h-3.5 text-muted" />
                <span className="text-sm font-medium text-foreground">{rule.name}</span>
              </div>
              <span className="inline-flex text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-card-elevated text-muted">
                {rule.rule_type}
              </span>
            </div>

            {(rule.threshold != null || rule.window_minutes != null) && (
              <div className="space-y-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                  Thresholds
                </span>
                <div className="flex items-center gap-3 text-xs text-foreground">
                  {rule.threshold != null && (
                    <span className="code-text">threshold: {rule.threshold}</span>
                  )}
                  {rule.window_minutes != null && (
                    <span className="code-text">window: {rule.window_minutes}m</span>
                  )}
                </div>
              </div>
            )}

            <ConfidenceBar value={alert.confidence ?? 0} />

            <RuleFeedbackStats
              falsePositiveCount={rule.false_positive_count}
              truePositiveCount={rule.true_positive_count}
            />
          </>
        ) : (
          <>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Crosshair className="w-3.5 h-3.5 text-muted" />
                <span className="text-xs text-muted">
                  Source: <span className="code-text">{alert.source || "Unknown"}</span>
                </span>
              </div>
            </div>
            <ConfidenceBar value={alert.confidence ?? 0} />
          </>
        )}
      </div>
    </Card>
  );
}

export const AlertDetectionExplanation = memo(AlertDetectionExplanationInner);
