"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import LiveSecurityFeed from "@/components/LiveSecurityFeed";
import { CardSkeleton, ChartSkeleton } from "@/components/ui/Skeleton";
import { PageHeader, Panel, StatCard } from "@/components/ui/Panel";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

function ExecutiveKpis() {
  const { data, isLoading } = useSiemQuery<{
    total_hosts: number;
    online_hosts: number;
    active_alerts: number;
    critical_alerts: number;
    total_events: number;
    average_risk_score: number;
    most_attacked_host: string | null;
    most_attacked_count: number;
  }>("executive");

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {Array.from({ length: 7 }).map((_, i) => <CardSkeleton key={i} />)}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
      <StatCard label="Total hosts" value={data?.total_hosts} tone="info" />
      <StatCard label="Online" value={data?.online_hosts} tone="success" />
      <StatCard label="Active alerts" value={data?.active_alerts} tone="warning" />
      <StatCard label="Critical" value={data?.critical_alerts} tone="danger" />
      <StatCard label="Period events" value={data?.total_events} />
      <StatCard label="Avg risk" value={data?.average_risk_score} tone="warning" />
      <StatCard label="Top target" value={data?.most_attacked_host || "—"} tone="danger" />
    </div>
  );
}

function SecurityTrendWidget() {
  const { data, isLoading } = useSiemQuery<{ security_trend: { period: string; count: number }[] }>("executive");
  const trendData = useMemo(
    () => (data?.security_trend ?? []).slice(-60).map((p) => ({ period: String(p.period).slice(5, 16), count: p.count })),
    [data],
  );

  if (isLoading) return <ChartSkeleton height={200} />;
  if (!trendData.length) return null;

  return (
    <Panel title="Security trend">
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={trendData}>
          <XAxis dataKey="period" tick={{ fontSize: 10, fill: "#7b8ba3" }} stroke="#243044" />
          <YAxis stroke="#7b8ba3" width={32} />
          <Tooltip contentStyle={{ background: "#111820", border: "1px solid #243044" }} />
          <Line type="monotone" dataKey="count" stroke="#ff6b6b" dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </Panel>
  );
}

function RiskyHostsWidget() {
  const { data = [], isLoading } = useSiemQuery<{ host_id: string; host_name: string; risk_score: number; active_alerts: number }[]>(
    "top-risky-hosts",
    {},
  );

  return (
    <Panel title="Top risky hosts">
      {isLoading ? <ChartSkeleton height={120} /> : (
        <div className="space-y-2">
          {data.slice(0, 8).map((h) => (
            <div key={h.host_id} className="flex items-center gap-2 text-sm">
              <span className="w-24 truncate">{h.host_name}</span>
              <div className="flex-1 h-2 bg-[#0a1018] rounded overflow-hidden">
                <div className="h-full bg-[var(--danger)]" style={{ width: `${h.risk_score}%` }} />
              </div>
              <span className="w-6 tabular-nums text-xs">{h.risk_score}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function TimelinesWidget() {
  const { data = [], isLoading } = useSiemQuery<
    { id: string; host_name: string; title: string; risk_level: string; events: { event_type: string; description?: string }[] }[]
  >("attack-timelines");

  return (
    <Panel title="Attack timelines">
      {isLoading ? <ChartSkeleton height={120} /> : (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {data.slice(0, 5).map((t) => (
            <div key={t.id} className="p-2 border border-[var(--border-subtle)] rounded text-sm">
              <p className="font-medium">{t.host_name}: {t.title}</p>
              <p className="text-[11px] text-[var(--muted)]">Risk: {t.risk_level}</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function HistoricalWidget() {
  const [view, setView] = useState<"daily" | "weekly" | "monthly">("daily");
  const { data, isLoading } = useQuery({
    queryKey: ["siem", "historical", view],
    queryFn: () => api<{ events: { period: string; count: number }[]; alerts: { period: string; count: number }[] }>(`/api/v1/siem/historical?view=${view}`),
    staleTime: 120_000,
  });

  return (
    <Panel
      title="90-day history"
      action={
        <select value={view} onChange={(e) => setView(e.target.value as typeof view)} className="input-siem text-xs py-1">
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      }
    >
      {isLoading ? <ChartSkeleton height={100} /> : (
        <div className="grid md:grid-cols-2 gap-4 text-xs font-mono max-h-40 overflow-y-auto">
          <div>{data?.events.slice(-10).map((r) => <div key={r.period} className="flex justify-between py-0.5"><span>{r.period.slice(0, 10)}</span><span>{r.count}</span></div>)}</div>
          <div>{data?.alerts.slice(-10).map((r) => <div key={r.period} className="flex justify-between py-0.5"><span>{r.period.slice(0, 10)}</span><span>{r.count}</span></div>)}</div>
        </div>
      )}
    </Panel>
  );
}

function FeedWidget() {
  const { queryParams } = useTimeRange();
  const { data } = useQuery({
    queryKey: ["events", "feed", queryParams],
    queryFn: async () => {
      const q = buildQuery({ page_size: 15 }, queryParams);
      const r = await api<{ items?: { id: string; timestamp: string; event_type: string; severity: string; description: string | null }[] }>(`/api/v1/events${q}`);
      return Array.isArray(r) ? r : r.items || [];
    },
    staleTime: 20_000,
  });
  const initial = (data ?? []).map((e) => ({ id: e.id, timestamp: e.timestamp, severity: e.severity, event_type: e.event_type, description: e.description }));

  return (
    <Panel title="Live security feed" subtitle="Real-time events via WebSocket">
      <LiveSecurityFeed initial={initial} />
    </Panel>
  );
}

export default function ExecutiveDashboard() {
  return (
    <div className="space-y-5">
      <PageHeader title="Executive dashboard" subtitle="Operational summary across your environment" />
      <TimeRangeBar />
      <ExecutiveKpis />
      <SecurityTrendWidget />
      <div className="grid lg:grid-cols-2 gap-5">
        <RiskyHostsWidget />
        <TimelinesWidget />
      </div>
      <HistoricalWidget />
      <FeedWidget />
    </div>
  );
}
