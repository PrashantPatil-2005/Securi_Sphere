"use client";

import { memo } from "react";
import Link from "next/link";
import { ArrowLeft, Clock, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { SeverityBadge, StatusBadge } from "@/components/design-system";
import type { Alert } from "@/lib/types/alert";

interface AlertDetailHeaderProps {
  alert: Alert;
  hostName?: string;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.max(0, Math.round((now - then) / 1000));

  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function AlertDetailHeaderInner({ alert, hostName }: AlertDetailHeaderProps) {
  const severityKey = (alert.severity?.toLowerCase() || "info") as
    | "critical"
    | "high"
    | "medium"
    | "low"
    | "info";

  return (
    <div className="space-y-4">
      <Link
        href="/alerts"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-muted hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Alerts
      </Link>

      <div
        className={cn(
          "panel border-l-4 p-5",
          `border-l-severity-${severityKey}`,
        )}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2 min-w-0 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <SeverityBadge severity={alert.severity} className="text-xs" />
              {hostName && (
                <span className="text-xs text-muted">{hostName}</span>
              )}
            </div>
            <h1 className="text-lg font-semibold text-foreground leading-snug">
              {alert.title}
            </h1>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            {alert.confidence != null && (
              <div className="flex items-center gap-1.5 text-xs text-muted">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span className="font-medium tabular-nums">{alert.confidence}%</span>
                <span>confidence</span>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 mt-3 flex-wrap">
          <StatusBadge status={alert.status} />
          <div className="flex items-center gap-1 text-[11px] text-muted">
            <Clock className="w-3 h-3" />
            Detected {formatRelativeTime(alert.created_at)}
          </div>
        </div>
      </div>
    </div>
  );
}

export const AlertDetailHeader = memo(AlertDetailHeaderInner);
