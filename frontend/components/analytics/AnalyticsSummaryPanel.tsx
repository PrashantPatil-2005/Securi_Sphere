"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Panel, StatCard } from "@/components/ui/Panel";
import { Select } from "@/components/ui/Select";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";

interface Summary {
  events_today: number;
  events_this_week: number;
  events_this_month: number;
  alerts_today: number;
  alerts_this_week: number;
  alerts_this_month: number;
}

interface RetentionBucket {
  period: string;
  count: number;
}

interface RetentionResponse {
  view: string;
  since: string;
  events: RetentionBucket[];
  alerts: RetentionBucket[];
}

export function AnalyticsSummaryPanel() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["analytics", "summary"],
    queryFn: () => api<Summary>("/api/v1/analytics/summary"),
    staleTime: 60_000,
  });

  if (isLoading) return <ChartSkeleton height={120} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <Panel title="Activity summary" subtitle="Event and alert volume across day, week, and month">
      <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Events today" value={data?.events_today ?? 0} />
        <StatCard label="Events this week" value={data?.events_this_week ?? 0} />
        <StatCard label="Events this month" value={data?.events_this_month ?? 0} />
        <StatCard label="Alerts today" value={data?.alerts_today ?? 0} tone="warning" />
        <StatCard label="Alerts this week" value={data?.alerts_this_week ?? 0} tone="warning" />
        <StatCard label="Alerts this month" value={data?.alerts_this_month ?? 0} tone="warning" />
      </div>
    </Panel>
  );
}

export function AnalyticsRetentionPanel() {
  const [view, setView] = useState<"daily" | "weekly" | "monthly">("daily");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["analytics", "retention", view],
    queryFn: () => api<RetentionResponse>(`/api/v1/analytics/retention?view=${view}`),
    staleTime: 60_000,
  });

  const maxCount = Math.max(
    1,
    ...(data?.events.map((e) => e.count) ?? []),
    ...(data?.alerts.map((a) => a.count) ?? []),
  );

  return (
    <Panel
      title="Retention view"
      subtitle="Bucketed event and alert counts for the last 90 days"
      action={
        <Select
          label="Bucket"
          value={view}
          onChange={(e) => setView(e.target.value as typeof view)}
          className="min-w-[140px]"
        >
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </Select>
      }
    >
      {isLoading && <ChartSkeleton height={200} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {data && (
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <p className="text-caption normal-case text-muted mb-2">Events</p>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {data.events.length === 0 && <p className="text-sm text-muted">No events in range.</p>}
              {data.events.map((row) => (
                <div key={row.period} className="flex items-center gap-2 text-xs">
                  <span className="w-28 truncate text-muted">{row.period.slice(0, 10)}</span>
                  <div className="flex-1 h-2 bg-[var(--input-bg)] rounded">
                    <div className="h-full bg-accent rounded" style={{ width: `${(row.count / maxCount) * 100}%` }} />
                  </div>
                  <span className="w-8 tabular-nums">{row.count}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="text-caption normal-case text-muted mb-2">Alerts</p>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {data.alerts.length === 0 && <p className="text-sm text-muted">No alerts in range.</p>}
              {data.alerts.map((row) => (
                <div key={row.period} className="flex items-center gap-2 text-xs">
                  <span className="w-28 truncate text-muted">{row.period.slice(0, 10)}</span>
                  <div className="flex-1 h-2 bg-[var(--input-bg)] rounded">
                    <div className="h-full bg-warning rounded" style={{ width: `${(row.count / maxCount) * 100}%` }} />
                  </div>
                  <span className="w-8 tabular-nums">{row.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}
