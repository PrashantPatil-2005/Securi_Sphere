"use client";

import { memo } from "react";
import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useTimeRange } from "@/lib/timeRange";
import { useSimulationQueryParams } from "@/lib/simulation-session";
import { SeverityBadge, StatusBadge } from "@/components/design-system";
import { LoadingState } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { EmptyState } from "@/components/design-system/EmptyState";
import { ArrowRight } from "lucide-react";

interface Offense {
  id: string;
  offense_number: number;
  host_name: string;
  title: string;
  risk_level: string;
  status: string;
  event_count: number;
  created_at: string;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export const RecentOffenses = memo(function RecentOffenses() {
  const { queryParams } = useTimeRange();
  const simParams = useSimulationQueryParams();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["offenses", "dashboard", queryParams, simParams],
    queryFn: () => {
      const params = new URLSearchParams({ ...queryParams, ...simParams });
      params.set("page_size", "5");
      return api<{ items: Offense[]; total: number }>(`/api/v1/offenses?${params.toString()}`);
    },
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });

  if (isLoading && !data) return <LoadingState variant="table" rows={4} />;
  if (isError && !data) return <ErrorState variant="card" title="Failed to load offenses" onRetry={() => refetch()} />;

  const offenses = data?.items ?? [];

  if (!offenses.length) {
    return (
      <EmptyState
        title="No open offenses"
        description="Offenses appear when correlated alerts are grouped."
      />
    );
  }

  return (
    <div>
      <div className="space-y-1">
        {offenses.map((o) => (
          <Link
            key={o.id}
            href={`/offenses?id=${o.id}`}
            className="flex items-center gap-3 px-3 py-2.5 rounded-md hover:bg-[var(--sidebar-hover)] transition-colors group"
          >
            <SeverityBadge severity={o.risk_level} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate group-hover:text-accent transition-colors">
                {o.title}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[11px] text-muted">{o.host_name}</span>
                <span className="text-[10px] text-muted">·</span>
                <span className="text-[10px] text-muted tabular-nums">{o.event_count} events</span>
                <span className="text-[10px] text-muted">·</span>
                <span className="text-[10px] text-muted">{timeAgo(o.created_at)}</span>
              </div>
            </div>
            <StatusBadge status={o.status} />
          </Link>
        ))}
      </div>
      {data?.total && data.total > 5 && (
        <div className="mt-3 pt-3 border-t border-border-subtle">
          <Link href="/offenses" className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors">
            View all {data.total} offenses
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      )}
    </div>
  );
});
