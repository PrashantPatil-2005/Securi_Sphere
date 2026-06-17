"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import LiveSecurityFeed from "@/components/LiveSecurityFeed";
import { LazyEventTrendChart, LazySeverityCharts, LazyWidget } from "@/components/LazyWidget";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { ChartSkeleton } from "@/components/ui/Skeleton";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";

const CAT_COLORS = ["#4c9aff", "#ff6b6b", "#f5c842", "#3dd68c", "#a78bfa", "#f472b6", "#7b8ba3"];

export default function AnalyticsPage() {
  const { queryParams } = useTimeRange();
  const [hostFilter, setHostFilter] = useState("");
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

  const { data: trend, isLoading: trendLoading } = useSiemQuery<{
    total: { period: string; count: number }[];
    security: { period: string; count: number }[];
    authentication: { period: string; count: number }[];
    service: { period: string; count: number }[];
  }>("events-trend", extra);

  const { data: severity, isLoading: sevLoading } = useSiemQuery<{ distribution: { severity: string; count: number; percentage: number }[] }>(
    "severity-distribution",
    extra,
  );

  const { data: eventTypes, isLoading: typesLoading } = useSiemQuery<{
    categories: { category: string; count: number }[];
    trend: Record<string, unknown>[];
  }>("event-types", hostExtra);

  const { data: failedLogins, isLoading: failLoading } = useSiemQuery<Record<string, unknown>>("failed-logins", hostExtra);
  const { data: riskyHosts = [] } = useSiemQuery<{ host_name: string; risk_score: number; color: string; active_alerts: number }[]>("top-risky-hosts");
  const { data: health } = useSiemQuery<{ hosts: { host_name: string; health_status: string; health_score: number }[] }>("host-health");

  const { data: feedData } = useQuery({
    queryKey: ["events", "feed", queryParams],
    queryFn: async () => {
      const q = buildQuery({ page_size: 20 }, queryParams);
      const r = await api<{ items?: { id: string; timestamp: string; event_type: string; severity: string; description: string | null }[] }>(`/api/v1/events${q}`);
      return Array.isArray(r) ? r : r.items || [];
    },
    staleTime: 30_000,
  });

  const feedInitial = (feedData ?? []).map((e) => ({
    id: e.id,
    timestamp: e.timestamp,
    severity: e.severity,
    event_type: e.event_type,
    description: e.description,
  }));

  return (
    <div className="space-y-5">
      <PageHeader title="SIEM analytics" subtitle="Trends, distributions, and threat indicators" />
      <TimeRangeBar />
      <div className="filter-bar">
        <input placeholder="Host ID filter" value={hostFilter} onChange={(e) => setHostFilter(e.target.value)} className="input-siem" />
        <select value={alertStatus} onChange={(e) => setAlertStatus(e.target.value)} className="input-siem">
          <option value="">All alert statuses</option>
          <option value="open">Open</option>
          <option value="investigating">Investigating</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      <Panel title="Security events trend">
        {trendLoading || !trend ? <ChartSkeleton /> : (
          <LazyWidget>
            <LazyEventTrendChart {...trend} />
          </LazyWidget>
        )}
      </Panel>

      <Panel title="Alert severity distribution">
        {sevLoading || !severity ? <ChartSkeleton /> : (
          <LazyWidget>
            <LazySeverityCharts distribution={severity.distribution} />
          </LazyWidget>
        )}
      </Panel>

      <div className="grid lg:grid-cols-2 gap-5">
        <Panel title="Event type distribution">
          {typesLoading ? <ChartSkeleton height={260} /> : eventTypes && (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={eventTypes.categories} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={88} isAnimationActive={false}>
                  {eventTypes.categories.map((_, i) => <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#111820", border: "1px solid #243044" }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Panel>
        <Panel title="Category trend">
          {typesLoading ? <ChartSkeleton height={260} /> : eventTypes && (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={eventTypes.trend.slice(-60)}>
                <XAxis dataKey="period" tick={{ fontSize: 9, fill: "#7b8ba3" }} tickFormatter={(v) => String(v).slice(5, 16)} />
                <YAxis stroke="#7b8ba3" width={32} />
                <Tooltip contentStyle={{ background: "#111820", border: "1px solid #243044" }} />
                {eventTypes.categories.map((c, i) => (
                  <Line key={c.category} type="monotone" dataKey={c.category} stroke={CAT_COLORS[i % CAT_COLORS.length]} dot={false} isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      <Panel title="Failed login analytics">
        {failLoading ? <ChartSkeleton /> : failedLogins && (
          <div className="grid md:grid-cols-2 gap-6">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={(failedLogins.over_time as { period: string; count: number }[])?.slice(-60) || []}>
                <XAxis dataKey="period" tick={{ fontSize: 9, fill: "#7b8ba3" }} tickFormatter={(v) => String(v).slice(5, 16)} />
                <YAxis stroke="#7b8ba3" width={32} />
                <Tooltip contentStyle={{ background: "#111820", border: "1px solid #243044" }} />
                <Bar dataKey="count" fill="#ff6b6b" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-[11px] uppercase text-[var(--muted)] mb-2">Top attacking IPs</p>
                {((failedLogins.top_attacking_ips as { source_ip: string; count: number }[]) || []).slice(0, 8).map((r) => (
                  <div key={r.source_ip} className="flex justify-between py-1 border-b border-[var(--border-subtle)]"><span className="font-mono text-xs">{r.source_ip}</span><span className="text-[var(--danger)]">{r.count}</span></div>
                ))}
              </div>
              <div>
                <p className="text-[11px] uppercase text-[var(--muted)] mb-2">Targeted accounts</p>
                {((failedLogins.most_targeted_accounts as { username: string; count: number }[]) || []).slice(0, 8).map((r) => (
                  <div key={r.username} className="flex justify-between py-1 border-b border-[var(--border-subtle)]"><span>{r.username}</span><span className="text-[var(--warning)]">{r.count}</span></div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Panel>

      <div className="grid lg:grid-cols-2 gap-5">
        <Panel title="Top risky hosts">
          <div className="space-y-2">
            {riskyHosts.map((h) => (
              <div key={h.host_name} className="flex items-center gap-2 text-sm">
                <span className="w-28 truncate">{h.host_name}</span>
                <div className="flex-1 h-2 bg-[#0a1018] rounded"><div className="h-full bg-[var(--danger)]" style={{ width: `${h.risk_score}%` }} /></div>
                <span className="w-8 tabular-nums text-xs">{h.risk_score}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Host health">
          {(health?.hosts || []).map((h) => (
            <div key={h.host_name} className="flex justify-between py-2 border-b border-[var(--border-subtle)] text-sm">
              <span>{h.host_name}</span>
              <span className={h.health_status === "critical" ? "text-[var(--danger)]" : h.health_status === "warning" ? "text-[var(--warning)]" : "text-[var(--success)]"}>
                {h.health_status} ({h.health_score})
              </span>
            </div>
          ))}
        </Panel>
      </div>

      <Panel title="Live security feed">
        <LiveSecurityFeed initial={feedInitial} />
      </Panel>
    </div>
  );
}
