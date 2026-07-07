"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, Shield } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils/cn";

export interface ThreatScore {
  host_id: string;
  host_name: string;
  score: number;
  health_score: number;
  factors: Record<string, number>;
}

interface ThreatScoresPanelProps {
  onSelectHost?: (hostId: string) => void;
  /** Max rows to show; omit to show all. */
  limit?: number;
  showFactors?: boolean;
  viewAllHref?: string;
}

export function ThreatScoresPanel({
  onSelectHost,
  limit,
  showFactors = false,
  viewAllHref,
}: ThreatScoresPanelProps) {
  const { data: scores = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["threat-scores"],
    queryFn: () => api<ThreatScore[]>("/api/v1/threat-scores"),
    staleTime: 30_000,
  });

  if (isLoading) return <TableSkeleton rows={5} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

  const visible = limit != null ? scores.slice(0, limit) : scores;
  const hasMore = limit != null && scores.length > limit;

  return (
    <Panel
      title="Threat score leaderboard"
      subtitle="Ranked hosts by composite threat score (alerts, severity, health)"
      action={
        viewAllHref && hasMore ? (
          <Link href={viewAllHref} className="text-xs text-accent hover:underline inline-flex items-center gap-1">
            View all
            <ArrowRight className="w-3 h-3" />
          </Link>
        ) : undefined
      }
    >
      {scores.length === 0 ? (
        <EmptyState
          title="No threat scores yet"
          description="Run Attack Lab or enroll agents to populate host risk scoring."
          icon={<Shield className="w-8 h-8" />}
          action="/simulation"
          actionLabel="Open Attack Lab"
        />
      ) : (
        <div className="space-y-2">
          {visible.map((s, i) => (
            <button
              key={s.host_id}
              type="button"
              onClick={() => onSelectHost?.(s.host_id)}
              className={cn(
                "flex flex-col gap-1 w-full text-left p-2 rounded-lg hover:bg-[var(--sidebar-hover)] transition-colors",
                showFactors && "p-3",
              )}
            >
              <div className="flex items-center gap-3 w-full">
                <span className="w-6 text-xs text-muted tabular-nums">#{i + 1}</span>
                <span className="w-28 truncate text-sm font-medium">{s.host_name}</span>
                <div className="flex-1 h-2 bg-[var(--input-bg)] rounded">
                  <div className="h-full bg-danger rounded" style={{ width: `${Math.min(s.score, 100)}%` }} />
                </div>
                <span className="w-10 text-xs tabular-nums text-danger font-semibold">{s.score}</span>
                <span className="w-14 text-xs text-muted">health {s.health_score}</span>
              </div>
              {showFactors && Object.keys(s.factors).length > 0 && (
                <div className="flex flex-wrap gap-1 pl-9">
                  {Object.entries(s.factors).map(([key, value]) => (
                    <span key={key} className="text-[10px] px-1.5 py-0.5 rounded bg-muted/15 text-muted">
                      {key.replace(/_/g, " ")}: {value}
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </Panel>
  );
}
