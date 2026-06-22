"use client";

import { memo, useMemo, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Server, Activity, Shield } from "lucide-react";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import TimeRangeBar from "@/components/TimeRangeBar";
import { HostRiskDrawer } from "@/components/HostRiskDrawer";
import { CardSkeleton, ChartSkeleton } from "@/components/ui/Skeleton";
import { PageHeader, Panel, StatCard, EmptyState } from "@/components/ui/Panel";
import { axisProps, CHART_THEME } from "@/lib/design/chartTheme";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const LiveSecurityFeed = dynamic(() => import("@/components/LiveSecurityFeed"), {
  loading: () => <ChartSkeleton height={280} />,
  ssr: false,
});

const ExecutiveKpis = memo(function ExecutiveKpis() {
  const { data, isLoading } = useSiemQuery<{
    total_hosts: number;
    online_hosts: number;
    active_alerts: number;
    critical_alerts: number;
    average_risk_score: number;
  }>("executive");

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
      </div>
    );
  }

  const healthPct = data?.total_hosts ? Math.round((data.online_hosts / data.total_hosts) * 100) : 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <StatCard label="Total hosts" value={data?.total_hosts} tone="info" href="/hosts" />
      <StatCard label="Host health" value={`${healthPct}%`} tone={healthPct >= 80 ? "success" : healthPct >= 50 ? "warning" : "danger"} href="/hosts" />
      <StatCard label="Active alerts" value={data?.active_alerts} tone="warning" href="/alerts" />
      <StatCard label="Critical alerts" value={data?.critical_alerts} tone="danger" href="/alerts" />
      <StatCard label="Threat score" value={data?.average_risk_score} tone="warning" href="/analytics" />
      <StatCard label="Online hosts" value={`${data?.online_hosts ?? 0}/${data?.total_hosts ?? 0}`} tone="success" href="/hosts" />
    </div>
  );
});

const SecurityTimeline = memo(function SecurityTimeline() {
  const { data, isLoading } = useSiemQuery<{ security_trend: { period: string; count: number }[] }>("executive");
  const trendData = useMemo(
    () => (data?.security_trend ?? []).slice(-48).map((p) => ({
      period: String(p.period).slice(5, 16),
      count: p.count,
    })),
    [data],
  );

  if (isLoading) return <ChartSkeleton height={240} />;

  if (!trendData.length) {
    return (
      <EmptyState
        title="No security events"
        description="Events will appear here as your agents begin reporting."
        action="/hosts"
        actionLabel="Add hosts"
        icon={<Activity className="w-10 h-10 opacity-40" />}
      />
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={trendData}>
        <defs>
          <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CHART_THEME.colors.primary} stopOpacity={0.3} />
            <stop offset="100%" stopColor={CHART_THEME.colors.primary} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="period" {...axisProps} />
        <YAxis {...axisProps} width={36} />
        <Tooltip {...CHART_THEME.tooltip} />
        <Area type="monotone" dataKey="count" stroke={CHART_THEME.colors.primary} fill="url(#trendGrad)" strokeWidth={2} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
});

const RiskyHostsWidget = memo(function RiskyHostsWidget({ onSelect }: { onSelect: (id: string) => void }) {
  const { data = [], isLoading } = useSiemQuery<{ host_id: string; host_name: string; risk_score: number }[]>("top-risky-hosts", {});

  if (isLoading) return <ChartSkeleton height={200} />;

  if (!data.length) {
    return (
      <EmptyState
        title="No hosts monitored"
        description="Deploy agents to start tracking host risk scores."
        action="/hosts"
        actionLabel="Manage hosts"
        icon={<Server className="w-10 h-10 opacity-40" />}
      />
    );
  }

  return (
    <div className="space-y-3">
      {data.slice(0, 6).map((h) => (
        <button key={h.host_id} type="button" onClick={() => onSelect(h.host_id)} className="flex items-center gap-3 group w-full text-left">
          <span className="w-28 truncate text-body group-hover:text-accent transition-colors">{h.host_name}</span>
          <div className="flex-1 h-2 bg-[var(--input-bg)] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${h.risk_score}%`,
                backgroundColor: h.risk_score > 70 ? CHART_THEME.colors.danger : h.risk_score > 40 ? CHART_THEME.colors.warning : CHART_THEME.colors.success,
              }}
            />
          </div>
          <span className="w-8 tabular-nums text-caption normal-case text-right">{h.risk_score}</span>
        </button>
      ))}
    </div>
  );
});

const AttackTimelines = memo(function AttackTimelines() {
  const { data = [], isLoading } = useSiemQuery<
    { id: string; host_name: string; title: string; risk_level: string }[]
  >("attack-timelines");

  if (isLoading) return <ChartSkeleton height={200} />;

  if (!data.length) {
    return (
      <EmptyState
        title="No active timelines"
        description="Attack timelines are generated when correlated events are detected."
        icon={<Shield className="w-10 h-10 opacity-40" />}
      />
    );
  }

  return (
    <div className="space-y-2">
      {data.slice(0, 5).map((t) => (
        <Link
          key={t.id}
          href="/timeline"
          className="block p-3 rounded-lg border border-border-subtle hover:border-border hover:bg-[var(--sidebar-hover)] transition-all duration-fast"
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-body font-medium truncate">{t.title}</p>
            <span className={`badge badge-${t.risk_level === "critical" ? "critical" : t.risk_level === "high" ? "high" : "medium"}`}>
              {t.risk_level}
            </span>
          </div>
          <p className="text-caption normal-case text-muted mt-1">{t.host_name}</p>
        </Link>
      ))}
    </div>
  );
});

export default function ExecutiveDashboard() {
  const [riskHostId, setRiskHostId] = useState<string | null>(null);
  return (
    <div className="space-y-6">
      <PageHeader
        title="Security Operations"
        subtitle="Real-time overview of your security posture"
        action={<TimeRangeBar />}
      />

      <ExecutiveKpis />

      <Panel title="Security timeline" subtitle="Event volume over selected period">
        <SecurityTimeline />
      </Panel>

      <div className="grid lg:grid-cols-2 gap-6">
        <Panel title="Host risk ranking" subtitle="Highest risk scores in your environment">
          <RiskyHostsWidget onSelect={setRiskHostId} />
        </Panel>
        <Panel title="Active attack timelines" subtitle="Correlated threat sequences">
          <AttackTimelines />
        </Panel>
      </div>

      <Panel title="Live security feed" subtitle="Real-time events via WebSocket">
        <LiveSecurityFeed initial={[]} />
      </Panel>
      <HostRiskDrawer hostId={riskHostId} onClose={() => setRiskHostId(null)} />
    </div>
  );
}
