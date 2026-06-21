"use client";

import { useEffect, useMemo, useState } from "react";
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

interface Metric {
  recorded_at: string;
  cpu_percent: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
}

export default function MetricsPage() {
  const { queryParams } = useTimeRange();
  const { data: hosts = [], isLoading: hostsLoading } = useHostsList();
  const [hostId, setHostId] = useState("");

  useEffect(() => {
    if (!hostId && hosts[0]) setHostId(hosts[0].id);
  }, [hosts, hostId]);

  const { data: metrics = [], isLoading: metricsLoading } = useQuery({
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
      {hostsLoading || metricsLoading ? (
        <TableSkeleton rows={6} />
      ) : chartData.length > 0 ? (
        <Panel title="Utilization">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="time" stroke="#666" fontSize={11} />
                <YAxis stroke="#666" domain={[0, 100]} fontSize={11} />
                <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2f3b4f" }} />
                <Legend />
                <Line type="monotone" dataKey="cpu" stroke="#3b82f6" dot={false} isAnimationActive={false} name="CPU %" />
                <Line type="monotone" dataKey="memory" stroke="#22c55e" dot={false} isAnimationActive={false} name="Memory %" />
                <Line type="monotone" dataKey="disk" stroke="#eab308" dot={false} isAnimationActive={false} name="Disk %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      ) : (
        <EmptyState title="No metrics" description="No metrics for the selected host and time range." />
      )}
    </div>
  );
}
