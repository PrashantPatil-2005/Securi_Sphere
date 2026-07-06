"use client";

import { useEffect, useMemo, useState } from "react";
import { Gauge } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { downsampleSeries } from "@/lib/downsample";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { axisProps, CHART_THEME } from "@/lib/design/chartTheme";

interface Metric {
  recorded_at: string;
  cpu_percent: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
}

export default function MetricsPage() {
  const { queryParams } = useTimeRange();
  const { data: hosts = [], isLoading: hostsLoading, isError: hostsError, refetch: refetchHosts } = useHostsList();
  const [hostId, setHostId] = useState("");

  useEffect(() => {
    if (!hostId && hosts[0]) setHostId(hosts[0].id);
  }, [hosts, hostId]);

  const { data: metrics = [], isLoading: metricsLoading, isError: metricsError, refetch: refetchMetrics } = useQuery({
    queryKey: ["metrics", hostId, queryParams],
    queryFn: async () => {
      const q = buildQuery({ host_id: hostId, limit: 500 }, queryParams);
      return api<Metric[]>(`/api/v1/metrics${q}`);
    },
    enabled: !!hostId,
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  const chartData = useMemo(
    () =>
      downsampleSeries(metrics, 120).map((m) => ({
        time: new Date(m.recorded_at).toLocaleTimeString(),
        cpu: m.cpu_percent,
        memory: m.memory_percent,
        disk: m.disk_percent,
      })),
    [metrics],
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Host Metrics" subtitle="CPU, memory, and disk utilization over time" />
      <TimeRangeBar />
      <select value={hostId} onChange={(e) => setHostId(e.target.value)} className="input-siem max-w-xs">
        {hosts.map((h) => (
          <option key={h.id} value={h.id}>
            {h.name}
          </option>
        ))}
      </select>
      {hostsError ? (
        <QueryError onRetry={() => refetchHosts()} />
      ) : metricsError ? (
        <QueryError onRetry={() => refetchMetrics()} />
      ) : hostsLoading || metricsLoading ? (
        <TableSkeleton rows={6} />
      ) : chartData.length > 0 ? (
        <Panel title="Utilization">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="time" {...axisProps} />
                <YAxis {...axisProps} domain={[0, 100]} width={36} />
                <Tooltip {...CHART_THEME.tooltip} />
                <Legend />
                <Line type="monotone" dataKey="cpu" stroke={CHART_THEME.colors.primary} dot={false} isAnimationActive={false} name="CPU %" />
                <Line type="monotone" dataKey="memory" stroke={CHART_THEME.colors.success} dot={false} isAnimationActive={false} name="Memory %" />
                <Line type="monotone" dataKey="disk" stroke={CHART_THEME.colors.warning} dot={false} isAnimationActive={false} name="Disk %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      ) : (
        <EmptyState
          title="No metrics"
          description="Select a host with an enrolled agent, or widen the time range."
          icon={<Gauge className="w-10 h-10 opacity-40" />}
          action="/hosts"
          actionLabel="View hosts"
        />
      )}
    </div>
  );
}
