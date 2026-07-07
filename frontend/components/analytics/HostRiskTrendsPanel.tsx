"use client";

import { useMemo } from "react";
import { useSiemQuery, useHostsList } from "@/lib/hooks/useApiQuery";
import { HostRiskTrendChart } from "@/components/charts/HostRiskTrendChart";
import { Panel } from "@/components/ui/Panel";
import { Select } from "@/components/ui/Select";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { cn } from "@/lib/utils/cn";

interface TrendsData {
  bucket: string;
  fleet_average: { period: string; avg_risk: number; avg_health: number }[];
  series: {
    host_id: string;
    host_name: string;
    current_score: number;
    delta: number;
    points: { recorded_at: string; risk_score: number; health_score: number }[];
  }[];
  top_movers: {
    host_id: string;
    host_name: string;
    current_score: number;
    delta: number;
  }[];
}

interface HostRiskTrendsPanelProps {
  hostId?: string;
  onHostIdChange?: (hostId: string) => void;
  onSelectHost?: (hostId: string) => void;
}

export function HostRiskTrendsPanel({ hostId = "", onHostIdChange, onSelectHost }: HostRiskTrendsPanelProps) {
  const { data: hosts = [] } = useHostsList();
  const extra = useMemo(() => {
    const p: Record<string, string> = {};
    if (hostId) p.host_id = hostId;
    return p;
  }, [hostId]);

  const { data, isLoading, isError, refetch } = useSiemQuery<TrendsData>("risk-score-trends", extra);

  return (
    <Panel
      title="Host risk score trends"
      subtitle={`Threat score over time (${data?.bucket ?? "hour"} buckets for fleet average)`}
    >
      <div className="mb-4 max-w-xs">
        <Select
          label="Host focus"
          value={hostId}
          onChange={(e) => onHostIdChange?.(e.target.value)}
        >
          <option value="">Top risky hosts (fleet)</option>
          {hosts.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name}
            </option>
          ))}
        </Select>
      </div>

      {isLoading && <ChartSkeleton height={280} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {data && !isLoading && (
        <div className="space-y-4">
          <HostRiskTrendChart fleetAverage={data.fleet_average} series={data.series} showFleet={!hostId} />

          {data.top_movers.length > 0 && (
            <div>
              <h3 className="text-subheading mb-2">Top movers</h3>
              <div className="flex flex-wrap gap-2">
                {data.top_movers.map((m) => (
                  <button
                    key={m.host_id}
                    type="button"
                    onClick={() => onSelectHost?.(m.host_id)}
                    className="text-xs px-3 py-1.5 rounded-lg border border-border-subtle hover:border-accent/40 transition-colors"
                  >
                    <span className="font-medium">{m.host_name}</span>
                    <span
                      className={cn(
                        "ml-2 tabular-nums",
                        m.delta > 0 ? "text-danger" : m.delta < 0 ? "text-success" : "text-muted",
                      )}
                    >
                      {m.delta > 0 ? "+" : ""}
                      {m.delta}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
