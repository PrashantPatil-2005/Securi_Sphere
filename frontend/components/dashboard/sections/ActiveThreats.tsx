"use client";

import { memo } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { SeverityBadge, StatusBadge } from "@/components/design-system";
import { LoadingState } from "@/components/design-system/LoadingState";
import { EmptyState } from "@/components/design-system/EmptyState";
import { useTimeRange } from "@/lib/timeRange";

interface Alert {
  id: string;
  title: string;
  severity: string;
  status: string;
  host_name: string;
  source: string;
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

export const ActiveThreats = memo(function ActiveThreats() {
  const { queryParams } = useTimeRange();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["alerts", "active", queryParams],
    queryFn: () => {
      const params = new URLSearchParams(queryParams);
      params.set("page_size", "10");
      params.set("sort", "newest");
      params.append("status", "open");
      params.append("status", "investigating");
      return api<{ items: Alert[]; total: number }>(`/api/v1/alerts?${params.toString()}`);
    },
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });

  if (isLoading && !data) {
    return <LoadingState variant="table" rows={5} />;
  }

  if (isError && !data) {
    return (
      <div className="flex items-center gap-3 py-4 px-2 text-sm text-muted">
        <AlertTriangle className="w-4 h-4 text-danger shrink-0" />
        <span className="flex-1">Unable to load threats</span>
        <button
          type="button"
          onClick={() => refetch()}
          className="text-xs text-accent hover:underline shrink-0"
        >
          Retry
        </button>
      </div>
    );
  }

  const threats = (data?.items ?? []).filter(
    (a) => a.severity === "critical" || a.severity === "high",
  );

  if (!threats.length) {
    return (
      <EmptyState
        title="No active threats"
        description="Your environment currently has no active critical or high severity alerts."
        icon={<AlertTriangle className="w-7 h-7" />}
      />
    );
  }

  return (
    <div>
      <div className="space-y-1">
        {threats.slice(0, 6).map((alert) => (
          <Link
            key={alert.id}
            href={`/alerts?highlight=${alert.id}`}
            className="flex items-center gap-3 px-3 py-2.5 rounded-md hover:bg-[var(--sidebar-hover)] transition-colors group"
          >
            <SeverityBadge severity={alert.severity} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate group-hover:text-accent transition-colors">
                {alert.title}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                {alert.host_name && (
                  <span className="text-[11px] text-muted">{alert.host_name}</span>
                )}
                <span className="text-[10px] text-muted">·</span>
                <span className="text-[10px] text-muted tabular-nums">{timeAgo(alert.created_at)}</span>
              </div>
            </div>
            <StatusBadge status={alert.status} />
          </Link>
        ))}
      </div>
      {data?.total && data.total > 6 && (
        <div className="mt-3 pt-3 border-t border-border-subtle">
          <Link href="/alerts" className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors">
            View all {data.total} alerts
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      )}
    </div>
  );
});
