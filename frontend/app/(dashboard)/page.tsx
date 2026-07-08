"use client";

import { memo, useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { Server, Activity, Shield, LayoutGrid } from "lucide-react";
import { api } from "@/lib/api";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import TimeRangeBar from "@/components/TimeRangeBar";
import { HostRiskDrawer } from "@/components/HostRiskDrawer";
import { OnboardingChecklist } from "@/components/OnboardingChecklist";
import { DashboardCustomizer } from "@/components/dashboard/DashboardCustomizer";
import { SavedSearchWidget } from "@/components/dashboard/SavedSearchWidget";
import { savedSearchIdFromWidget } from "@/lib/dashboardWidgets";
import { CardSkeleton, ChartSkeleton } from "@/components/ui/Skeleton";
import { PageHeader, Panel, StatCard, EmptyState } from "@/components/ui/Panel";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { useUxEnabled } from "@/lib/featureFlags";
import { QueryError } from "@/components/ui/QueryError";
import { Button } from "@/components/ui/Button";
import { axisProps, CHART_THEME } from "@/lib/design/chartTheme";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const LiveSecurityFeed = dynamic(() => import("@/components/LiveSecurityFeed"), {
  loading: () => <ChartSkeleton height={280} />,
  ssr: false,
});

const KPI_SNAPSHOT_KEY = "securi_kpi_snapshot";

const ExecutiveKpis = memo(function ExecutiveKpis() {
  const vitalityEnabled = useUxEnabled("ux_dashboard_vitality_enabled");
  const { data, isLoading, isError, refetch } = useSiemQuery<{
    total_hosts: number;
    online_hosts: number;
    active_alerts: number;
    critical_alerts: number;
    average_risk_score: number;
  }>("executive");

  const [deltas, setDeltas] = useState<Record<string, number>>({});

  useEffect(() => {
    if (!vitalityEnabled || !data) return;
    const prevRaw = sessionStorage.getItem(KPI_SNAPSHOT_KEY);
    const prev = prevRaw ? (JSON.parse(prevRaw) as Record<string, number>) : null;
    if (prev) {
      setDeltas({
        active_alerts: (data.active_alerts ?? 0) - (prev.active_alerts ?? 0),
        critical_alerts: (data.critical_alerts ?? 0) - (prev.critical_alerts ?? 0),
        online_hosts: (data.online_hosts ?? 0) - (prev.online_hosts ?? 0),
      });
    }
    sessionStorage.setItem(
      KPI_SNAPSHOT_KEY,
      JSON.stringify({
        active_alerts: data.active_alerts,
        critical_alerts: data.critical_alerts,
        online_hosts: data.online_hosts,
      }),
    );
  }, [data, vitalityEnabled]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)}
      </div>
    );
  }

  if (isError) return <QueryError onRetry={() => refetch()} />;

  const healthPct = data?.total_hosts ? Math.round((data.online_hosts / data.total_hosts) * 100) : 0;
  const showVitality = vitalityEnabled && (data?.total_hosts ?? 0) > 0;

  return (
    <div className="space-y-4">
      {vitalityEnabled && (data?.total_hosts ?? 0) === 0 && (
        <EmotionBanner
          tone="calm"
          title="Your dashboard is ready — add your first signal"
          message="Run Attack Lab for an instant demo, or enroll a host for live telemetry."
        />
      )}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <StatCard label="Total hosts" value={data?.total_hosts} tone="info" href="/hosts" vital={showVitality} />
      <StatCard label="Host health" value={`${healthPct}%`} tone={healthPct >= 80 ? "success" : healthPct >= 50 ? "warning" : "danger"} href="/hosts" vital={showVitality} />
      <StatCard label="Active alerts" value={data?.active_alerts} tone="warning" href="/alerts" vital={showVitality} delta={showVitality ? deltas.active_alerts : undefined} deltaLabel="since last visit" />
      <StatCard label="Critical alerts" value={data?.critical_alerts} tone="danger" href="/alerts" vital={showVitality} delta={showVitality ? deltas.critical_alerts : undefined} deltaLabel="since last visit" />
      <StatCard label="Threat score" value={data?.average_risk_score} tone="warning" href="/analytics" vital={showVitality} />
      <StatCard label="Online hosts" value={`${data?.online_hosts ?? 0}/${data?.total_hosts ?? 0}`} tone="success" href="/hosts" vital={showVitality} delta={showVitality ? deltas.online_hosts : undefined} deltaLabel="since last visit" />
      </div>
    </div>
  );
});

const SecurityTimeline = memo(function SecurityTimeline() {
  const { data, isLoading, isError, refetch } = useSiemQuery<{ security_trend: { period: string; count: number }[] }>("executive");
  const trendData = useMemo(
    () => (data?.security_trend ?? []).slice(-48).map((p) => ({
      period: String(p.period).slice(5, 16),
      count: p.count,
    })),
    [data],
  );

  if (isLoading) return <ChartSkeleton height={240} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

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
  const { data = [], isLoading, isError, refetch } = useSiemQuery<{ host_id: string; host_name: string; risk_score: number }[]>("top-risky-hosts", {});

  if (isLoading) return <ChartSkeleton height={200} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

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
  const { data = [], isLoading, isError, refetch } = useSiemQuery<
    { id: string; host_name: string; title: string; risk_level: string }[]
  >("attack-timelines");

  if (isLoading) return <ChartSkeleton height={200} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

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
          href={`/timeline?timeline=${t.id}`}
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

function renderWidget(
  id: string,
  riskHostId: string | null,
  setRiskHostId: (id: string | null) => void,
) {
  switch (id) {
    case "kpis":
      return <ExecutiveKpis key={id} />;
    case "onboarding":
      return <OnboardingChecklist key={id} />;
    case "timeline":
      return (
        <Panel key={id} title="Security timeline" subtitle="Event volume over selected period">
          <SecurityTimeline />
        </Panel>
      );
    case "risky_hosts":
      return (
        <Panel key={id} title="Host risk ranking" subtitle="Highest risk scores in your environment">
          <RiskyHostsWidget onSelect={setRiskHostId} />
        </Panel>
      );
    case "attack_timelines":
      return (
        <Panel key={id} title="Active attack timelines" subtitle="Correlated threat sequences">
          <AttackTimelines />
        </Panel>
      );
    case "live_feed":
      return (
        <Panel key={id} title="Live security feed" subtitle="Real-time events via WebSocket">
          <LiveSecurityFeed initial={[]} />
        </Panel>
      );
    default: {
      const searchId = savedSearchIdFromWidget(id);
      if (searchId) return <SavedSearchWidget key={id} searchId={searchId} />;
      return null;
    }
  }
}

export default function ExecutiveDashboard() {
  const [riskHostId, setRiskHostId] = useState<string | null>(null);
  const [customizeOpen, setCustomizeOpen] = useState(false);

  const { data: layout } = useQuery({
    queryKey: ["dashboard-layout"],
    queryFn: () => api<{ widgets: { id: string; visible: boolean }[] }>("/api/v1/dashboard/layout"),
    staleTime: 120_000,
  });

  const visibleWidgets = (layout?.widgets ?? []).filter((w) => w.visible);
  const blocks: ReactNode[] = [];
  let i = 0;
  while (i < visibleWidgets.length) {
    const current = visibleWidgets[i];
    const next = visibleWidgets[i + 1];
    if (current.id === "risky_hosts" && next?.id === "attack_timelines") {
      blocks.push(
        <div key="risk-row" className="grid lg:grid-cols-2 gap-6">
          {renderWidget("risky_hosts", riskHostId, setRiskHostId)}
          {renderWidget("attack_timelines", riskHostId, setRiskHostId)}
        </div>,
      );
      i += 2;
      continue;
    }
    blocks.push(renderWidget(current.id, riskHostId, setRiskHostId));
    i += 1;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security Operations"
        subtitle="Real-time overview of your security posture"
        action={
          <div className="flex items-center gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => setCustomizeOpen(true)}>
              <LayoutGrid className="w-4 h-4" />
              Customize
            </Button>
            <TimeRangeBar />
          </div>
        }
      />

      {blocks}
      <HostRiskDrawer hostId={riskHostId} onClose={() => setRiskHostId(null)} />
      <DashboardCustomizer open={customizeOpen} onClose={() => setCustomizeOpen(false)} />
    </div>
  );
}
