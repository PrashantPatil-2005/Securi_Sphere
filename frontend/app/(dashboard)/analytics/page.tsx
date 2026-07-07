"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import { FilterBar } from "@/components/ui/FilterBar";
import { Select } from "@/components/ui/Select";
import { Input } from "@/components/ui/Input";
import { LazyEventTrendChart, LazySeverityCharts, LazyAnalyticsCharts, LazyWidget } from "@/components/LazyWidget";
import { UebaAnomaliesPanel } from "@/components/analytics/UebaAnomaliesPanel";
import { ThreatScoresPanel } from "@/components/analytics/ThreatScoresPanel";
import { AnalyticsRetentionPanel, AnalyticsSummaryPanel } from "@/components/analytics/AnalyticsSummaryPanel";
import { HostRiskTrendsPanel } from "@/components/analytics/HostRiskTrendsPanel";
import { HostRiskDrawer } from "@/components/HostRiskDrawer";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";

const LazyLiveSecurityFeed = dynamic(() => import("@/components/LiveSecurityFeed"), {
  loading: () => <ChartSkeleton height={280} />,
  ssr: false,
});

export default function AnalyticsPage() {
  const { queryParams } = useTimeRange();
  const [hostFilter, setHostFilter] = useState("");
  const [riskHostFilter, setRiskHostFilter] = useState("");
  const [riskDrawerHostId, setRiskDrawerHostId] = useState<string | null>(null);
  const [alertStatus, setAlertStatus] = useState("");
  const extra = useMemo<Record<string, string>>(() => {
    const p: Record<string, string> = {};
    if (hostFilter) p.host_id = hostFilter;
    if (alertStatus) p.status = alertStatus;
    return p;
  }, [hostFilter, alertStatus]);
  const hostExtra = useMemo<Record<string, string>>(() => {
    const p: Record<string, string> = {};
    if (hostFilter) p.host_id = hostFilter;
    return p;
  }, [hostFilter]);

  const { data: trend, isLoading: trendLoading, isError: trendError, refetch: refetchTrend } = useSiemQuery<{
    total: { period: string; count: number }[];
    security: { period: string; count: number }[];
    authentication: { period: string; count: number }[];
    service: { period: string; count: number }[];
  }>("events-trend", extra);

  const { data: severity, isLoading: sevLoading, isError: sevError, refetch: refetchSev } = useSiemQuery<{ distribution: { severity: string; count: number; percentage: number }[] }>(
    "severity-distribution",
    extra,
  );

  const { data: eventTypes, isLoading: typesLoading, isError: typesError, refetch: refetchTypes } = useSiemQuery<{
    categories: { category: string; count: number }[];
    trend: Record<string, unknown>[];
  }>("event-types", hostExtra);

  const { data: failedLogins, isLoading: failLoading, isError: failError, refetch: refetchFail } = useSiemQuery<Record<string, unknown>>("failed-logins", hostExtra);
  const { data: riskyHosts = [], isError: riskyError, refetch: refetchRisky } = useSiemQuery<{ host_id: string; host_name: string; risk_score: number; color: string; active_alerts: number }[]>("top-risky-hosts");
  const { data: health, isError: healthError, refetch: refetchHealth } = useSiemQuery<{ hosts: { host_name: string; health_status: string; health_score: number }[] }>("host-health");

  const { data: feedData } = useQuery({
    queryKey: ["events", "feed", queryParams],
    queryFn: async () => {
      const q = buildQuery({ page_size: 20 }, queryParams);
      const r = await api<{ items?: { id: string; timestamp: string; event_type: string; severity: string; description: string | null }[] }>(`/api/v1/events${q}`);
      return Array.isArray(r) ? r : r.items || [];
    },
    staleTime: 30_000,
  });

  const feedInitial = useMemo(
    () =>
      (feedData ?? []).map((e) => ({
        id: e.id,
        timestamp: e.timestamp,
        severity: e.severity,
        event_type: e.event_type,
        description: e.description,
      })),
    [feedData],
  );

  return (
    <div className="space-y-5">
      <PageHeader title="SIEM analytics" subtitle="Trends, distributions, UEBA baselines, and threat indicators" />
      <UebaAnomaliesPanel />
      <AnalyticsSummaryPanel />
      <TimeRangeBar />

      <HostRiskTrendsPanel
        hostId={riskHostFilter}
        onHostIdChange={setRiskHostFilter}
        onSelectHost={(id) => setRiskDrawerHostId(id)}
      />

      <ThreatScoresPanel
        limit={10}
        onSelectHost={(id) => setRiskDrawerHostId(id)}
        viewAllHref="/threat-scores"
      />

      <AnalyticsRetentionPanel />

      <FilterBar activeCount={hostFilter ? 1 : 0}>
        <Input
          label="Host ID"
          placeholder="Filter by host UUID"
          value={hostFilter}
          onChange={(e) => setHostFilter(e.target.value)}
          className="max-w-xs"
        />
        <Select label="Alert status" value={alertStatus} onChange={(e) => setAlertStatus(e.target.value)} className="min-w-[160px]">
          <option value="">All alert statuses</option>
          <option value="open">Open</option>
          <option value="investigating">Investigating</option>
          <option value="resolved">Resolved</option>
        </Select>
      </FilterBar>

      <Panel title="Security events trend">
        {trendError ? (
          <QueryError onRetry={() => refetchTrend()} />
        ) : trendLoading || !trend ? <ChartSkeleton /> : (
          <LazyWidget>
            <LazyEventTrendChart {...trend} />
          </LazyWidget>
        )}
      </Panel>

      <Panel title="Alert severity distribution">
        {sevError ? (
          <QueryError onRetry={() => refetchSev()} />
        ) : sevLoading || !severity ? <ChartSkeleton /> : (
          <LazyWidget>
            <LazySeverityCharts distribution={severity.distribution} />
          </LazyWidget>
        )}
      </Panel>

      {typesError || failError ? (
        <QueryError onRetry={() => { refetchTypes(); refetchFail(); }} />
      ) : typesLoading || failLoading ? (
        <ChartSkeleton height={260} />
      ) : eventTypes && failedLogins ? (
        <LazyWidget minHeight={460}>
          <LazyAnalyticsCharts eventTypes={eventTypes} failedLogins={failedLogins} />
        </LazyWidget>
      ) : null}

      <div className="grid lg:grid-cols-2 gap-5">
        <Panel title="Top risky hosts">
          {riskyError ? (
            <QueryError onRetry={() => refetchRisky()} />
          ) : riskyHosts.length === 0 ? (
            <EmptyState title="No risky hosts yet" description="Run Attack Lab or enroll agents to generate risk scores." />
          ) : (
          <div className="space-y-2">
            {riskyHosts.map((h) => (
              <button
                key={h.host_id}
                type="button"
                onClick={() => setRiskDrawerHostId(h.host_id)}
                className="flex items-center gap-2 text-sm w-full text-left hover:text-accent transition-colors"
              >
                <span className="w-28 truncate">{h.host_name}</span>
                <div className="flex-1 h-2 bg-[var(--input-bg)] rounded"><div className="h-full bg-[var(--danger)]" style={{ width: `${h.risk_score}%` }} /></div>
                <span className="w-8 tabular-nums text-xs">{h.risk_score}</span>
              </button>
            ))}
          </div>
          )}
        </Panel>
        <Panel title="Host health">
          {healthError ? (
            <QueryError onRetry={() => refetchHealth()} />
          ) : !(health?.hosts || []).length ? (
            <EmptyState title="No host health data" description="Enroll hosts and collect metrics to see health scores." />
          ) : (
          (health?.hosts || []).map((h) => (
            <div key={h.host_name} className="flex justify-between py-2 border-b border-[var(--border-subtle)] text-sm">
              <span>{h.host_name}</span>
              <span className={h.health_status === "critical" ? "text-[var(--danger)]" : h.health_status === "warning" ? "text-[var(--warning)]" : "text-[var(--success)]"}>
                {h.health_status} ({h.health_score})
              </span>
            </div>
          ))
          )}
        </Panel>
      </div>

      <Panel title="Live security feed">
        <LazyLiveSecurityFeed initial={feedInitial} />
      </Panel>

      <HostRiskDrawer hostId={riskDrawerHostId} onClose={() => setRiskDrawerHostId(null)} />
    </div>
  );
}
