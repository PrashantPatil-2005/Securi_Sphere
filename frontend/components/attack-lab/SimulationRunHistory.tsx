"use client";

import { useQuery } from "@tanstack/react-query";
import { RotateCcw, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils/cn";
import type { SimulationRunDetail, SimulationRunListResponse } from "@/lib/types/simulation";

interface Props {
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
  onReplay: (runId: string) => void;
  onReset: (runId: string) => void;
  replayPendingId?: string | null;
  resetPendingId?: string | null;
  showPurge: boolean;
  onPurge: () => void;
  purgePending: boolean;
}

export function SimulationRunHistory({
  selectedRunId,
  onSelect,
  onReplay,
  onReset,
  replayPendingId,
  resetPendingId,
  showPurge,
  onPurge,
  purgePending,
}: Props) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["simulation", "runs"],
    queryFn: () => api<SimulationRunListResponse>("/api/v1/simulation/runs?page_size=20"),
    refetchOnWindowFocus: false,
  });

  const items = data?.items ?? [];

  if (isLoading) return <TableSkeleton rows={5} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <GlassPanel>
      <h2 className="text-subheading mb-4">Run history</h2>
      {items.length === 0 ? (
        <p className="text-sm text-muted">No simulation runs yet. Run a preset or custom chain to see history here.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted border-b border-border-subtle">
                <th className="pb-2 pr-4 font-medium">Time</th>
                <th className="pb-2 pr-4 font-medium">Name</th>
                <th className="pb-2 pr-4 font-medium">Host</th>
                <th className="pb-2 pr-4 font-medium tabular-nums">Events</th>
                <th className="pb-2 pr-4 font-medium tabular-nums">Alerts</th>
                <th className="pb-2 pr-4 font-medium tabular-nums">Offenses</th>
                <th className="pb-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((run) => {
                const isCustom = run.scenario_id === "custom";
                return (
                  <tr
                    key={run.id}
                    className={cn(
                      "border-b border-border-subtle/60 cursor-pointer hover:bg-[var(--sidebar-hover)] transition-colors",
                      selectedRunId === run.id && "bg-accent/10",
                    )}
                    onClick={() => onSelect(run.id)}
                  >
                    <td className="py-2.5 pr-4 text-muted whitespace-nowrap">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 pr-4">
                      <span className="font-medium">{run.name}</span>
                      {isCustom && (
                        <span className="ml-2 text-[10px] uppercase text-muted">custom</span>
                      )}
                    </td>
                    <td className="py-2.5 pr-4 text-muted">{run.host_name ?? run.host_id.slice(0, 8)}</td>
                    <td className="py-2.5 pr-4 tabular-nums">{run.event_count}</td>
                    <td className="py-2.5 pr-4 tabular-nums">{run.alert_count}</td>
                    <td className="py-2.5 pr-4 tabular-nums">{run.offense_count}</td>
                    <td className="py-2.5">
                      <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        {!isCustom && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            disabled={replayPendingId === run.id}
                            loading={replayPendingId === run.id}
                            onClick={() => onReplay(run.id)}
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            Replay
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={resetPendingId === run.id}
                          loading={resetPendingId === run.id}
                          onClick={() => onReset(run.id)}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Reset
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {data && data.total > items.length && (
        <p className="text-xs text-muted mt-3">Showing {items.length} of {data.total} runs</p>
      )}

      {showPurge && items.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border-subtle flex items-center justify-between gap-3">
          <p className="text-xs text-muted">
            Clear every simulated event, alert, timeline and run on this instance.
          </p>
          <Button type="button" variant="ghost" size="sm" disabled={purgePending} loading={purgePending} onClick={onPurge}>
            <Trash2 className="w-3.5 h-3.5" />
            Purge all simulated data
          </Button>
        </div>
      )}
    </GlassPanel>
  );
}

export async function fetchSimulationRunDetail(runId: string): Promise<SimulationRunDetail> {
  return api<SimulationRunDetail>(`/api/v1/simulation/runs/${runId}`);
}
