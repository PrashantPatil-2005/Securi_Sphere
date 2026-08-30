"use client";

import { memo } from "react";
import Link from "next/link";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";
import { EmptyState } from "@/components/design-system/EmptyState";
import type { UebaAnomaly } from "@/lib/types/ueba";
import { uebaMetricLabel } from "@/lib/types/ueba";

interface UebaAnomalyListProps {
  anomalies: UebaAnomaly[];
  isLoading: boolean;
  onDismiss: (id: string) => void;
  onResolve: (id: string) => void;
}

function UebaAnomalyListInner({ anomalies, isLoading, onDismiss, onResolve }: UebaAnomalyListProps) {
  return (
    <Card>
      <CardHeader
        title="Anomalies"
        subtitle={`${anomalies.length} anomal${anomalies.length !== 1 ? "ies" : "y"}`}
      />
      <div className="divide-y divide-border-subtle max-h-[600px] overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 w-3/4 skeleton rounded" />
                <div className="h-3 w-1/2 skeleton rounded" />
              </div>
            ))}
          </div>
        ) : anomalies.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No anomalies"
              description="Run a UEBA scan to detect baseline deviations."
            />
          </div>
        ) : (
          anomalies.map((a) => (
            <div key={a.id} className="px-4 py-3 hover:bg-[var(--sidebar-hover)] transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-sm">{a.entity_label}</span>
                    <span className="text-[10px] text-muted capitalize">{a.entity_type}</span>
                    <SeverityBadge severity={a.severity} />
                  </div>
                  <p className="text-xs text-muted mt-0.5">
                    {uebaMetricLabel(a.metric)} · observed {a.observed_value} · z={a.z_score.toFixed(1)} · baseline μ={a.baseline_mean.toFixed(1)}
                  </p>
                  <p className="text-xs mt-1">{a.description}</p>
                  <p className="text-[10px] text-muted mt-1">{new Date(a.detected_at).toLocaleString()}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  {a.alert_id && (
                    <Link
                      href={`/alerts/${a.alert_id}`}
                      className="px-2 py-1 text-[10px] rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                    >
                      Alert
                    </Link>
                  )}
                  {a.entity_type === "host" && (
                    <Link
                      href={`/hosts/${a.entity_key}`}
                      className="px-2 py-1 text-[10px] rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                    >
                      Host
                    </Link>
                  )}
                  <button
                    type="button"
                    onClick={() => onDismiss(a.id)}
                    className="px-2 py-1 text-[10px] rounded text-muted hover:bg-[var(--sidebar-hover)] transition-colors"
                  >
                    Dismiss
                  </button>
                  <button
                    type="button"
                    onClick={() => onResolve(a.id)}
                    className="px-2 py-1 text-[10px] rounded text-success hover:bg-success/10 transition-colors"
                  >
                    Resolve
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

export const UebaAnomalyList = memo(UebaAnomalyListInner);
