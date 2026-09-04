"use client";

import { memo } from "react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { HostRiskHistoryChart } from "@/components/charts/HostRiskHistoryChart";
import { hostRiskColor } from "@/lib/types/host";
import type { HostRiskDetail } from "@/lib/types/host";
import { AnimatedNumber } from "@/components/design-system/AnimatedNumber";

interface HostRiskSectionProps {
  risk: HostRiskDetail | undefined;
  isLoading: boolean;
}

function HostRiskSectionInner({ risk, isLoading }: HostRiskSectionProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Risk Profile" />
        <div className="p-4 space-y-3">
          <div className="h-8 skeleton rounded" />
          <div className="h-4 skeleton rounded w-3/4" />
          <div className="h-4 skeleton rounded w-1/2" />
        </div>
      </Card>
    );
  }

  if (!risk) {
    return (
      <Card>
        <CardHeader title="Risk Profile" />
        <div className="p-4 text-sm text-muted">
          Risk data unavailable.
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Risk Profile" subtitle="Threat score and contributing factors" />
      <div className="p-4 space-y-5">
        {/* Score summary */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 rounded-lg bg-card-elevated border border-border-subtle">
            <p className={`text-2xl font-semibold tabular-nums ${hostRiskColor(risk.score)}`}>
              <AnimatedNumber value={risk.score} />
            </p>
            <p className="text-xs text-muted mt-1">Threat Score</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-card-elevated border border-border-subtle">
            <p className="text-2xl font-semibold tabular-nums text-success">
              <AnimatedNumber value={risk.health_score} />
            </p>
            <p className="text-xs text-muted mt-1">Health Score</p>
          </div>
        </div>

        {/* Risk factors */}
        {risk.factor_breakdown.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted uppercase tracking-wide">Risk Factors</h4>
            <div className="space-y-2">
              {risk.factor_breakdown.map((f) => (
                <div key={f.name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-foreground">{f.name}</span>
                    <span className="text-muted tabular-nums">{f.weight}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-card-elevated overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${f.weight}%`,
                        backgroundColor: f.weight >= 50 ? "var(--danger)" : f.weight >= 25 ? "var(--warning)" : "var(--accent)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Risk history chart */}
        {risk.history.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted uppercase tracking-wide mb-3">Score History</h4>
            <HostRiskHistoryChart history={risk.history} />
          </div>
        )}
      </div>
    </Card>
  );
}

export const HostRiskSection = memo(HostRiskSectionInner);
