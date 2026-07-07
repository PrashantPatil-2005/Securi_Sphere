"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Drawer } from "@/components/ui/Drawer";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { QueryError } from "@/components/ui/QueryError";
import { HostRiskHistoryChart } from "@/components/charts/HostRiskHistoryChart";
import { TableSkeleton } from "@/components/ui/Skeleton";

interface RiskData {
  host_id: string;
  host_name: string;
  score: number;
  health_score: number;
  factors: Record<string, number>;
  factor_breakdown: { name: string; value: number; weight: number }[];
  history: { risk_score: number; health_score: number; recorded_at: string }[];
}

export function HostRiskDrawer({
  hostId,
  onClose,
}: {
  hostId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["host-risk", hostId],
    queryFn: () => api<RiskData>(`/api/v1/hosts/${hostId}/risk`),
    enabled: !!hostId,
  });

  return (
    <Drawer
      open={!!hostId}
      onClose={onClose}
      title={data?.host_name ?? "Host risk"}
      description="Explainable threat score"
    >
      {isLoading && <TableSkeleton rows={5} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <GlassPanel padding className="text-center">
              <p className="text-3xl font-semibold tabular-nums text-danger">{data.score}</p>
              <p className="text-caption normal-case text-muted mt-1">Threat score</p>
            </GlassPanel>
            <GlassPanel padding className="text-center">
              <p className="text-3xl font-semibold tabular-nums text-success">{data.health_score}</p>
              <p className="text-caption normal-case text-muted mt-1">Health score</p>
            </GlassPanel>
          </div>
          <div>
            <h3 className="text-subheading mb-3">Risk factors</h3>
            <div className="space-y-2">
              {data.factor_breakdown.map((f) => (
                <div key={f.name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span>{f.name}</span>
                    <span className="text-muted tabular-nums">{f.weight}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-[var(--sidebar-hover)] overflow-hidden">
                    <div className="h-full bg-accent rounded-full" style={{ width: `${f.weight}%` }} />
                  </div>
                </div>
              ))}
              {data.factor_breakdown.length === 0 && (
                <p className="text-sm text-muted">No risk factors recorded yet.</p>
              )}
            </div>
          </div>
          {data.history.length > 0 && (
            <div>
              <h3 className="text-subheading mb-3">Score history</h3>
              <HostRiskHistoryChart history={data.history} />
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}
