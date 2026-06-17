"use client";

import { useCallback, useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";

interface Host {
  id: string;
  name: string;
}
interface Metric {
  recorded_at: string;
  cpu_percent: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
}

export default function MetricsPage() {
  const { queryParams } = useTimeRange();
  const [hosts, setHosts] = useState<Host[]>([]);
  const [hostId, setHostId] = useState("");
  const [metrics, setMetrics] = useState<Metric[]>([]);

  useEffect(() => {
    api<{ items?: Host[] } | Host[]>("/api/v1/hosts?page_size=500")
      .then((r) => {
        const { items } = parsePaginatedList(r);
        setHosts(items);
        if (items[0]) setHostId(items[0].id);
      })
      .catch(console.error);
  }, []);

  const load = useCallback(() => {
    if (!hostId) return;
    const q = buildQuery({ host_id: hostId, limit: 500 }, queryParams);
    api<Metric[]>(`/api/v1/metrics${q}`).then(setMetrics).catch(console.error);
  }, [hostId, queryParams]);

  useEffect(() => {
    load();
    const i = setInterval(load, 30000);
    return () => clearInterval(i);
  }, [load]);

  const chartData = metrics.map((m) => ({
    time: new Date(m.recorded_at).toLocaleTimeString(),
    cpu: m.cpu_percent,
    memory: m.memory_percent,
    disk: m.disk_percent,
  }));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Metrics</h1>
      <TimeRangeBar />
      <select
        value={hostId}
        onChange={(e) => setHostId(e.target.value)}
        className="mb-6 px-3 py-2 bg-black/30 border border-[var(--border)] rounded"
      >
        {hosts.map((h) => (
          <option key={h.id} value={h.id}>
            {h.name}
          </option>
        ))}
      </select>
      {chartData.length > 0 ? (
        <div className="h-80 bg-[var(--card)] border border-[var(--border)] rounded-lg p-4">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="time" stroke="#666" fontSize={11} />
              <YAxis stroke="#666" domain={[0, 100]} fontSize={11} />
              <Tooltip contentStyle={{ background: "#1a2332", border: "1px solid #2f3b4f" }} />
              <Legend />
              <Line type="monotone" dataKey="cpu" stroke="#3b82f6" dot={false} name="CPU %" />
              <Line type="monotone" dataKey="memory" stroke="#22c55e" dot={false} name="Memory %" />
              <Line type="monotone" dataKey="disk" stroke="#eab308" dot={false} name="Disk %" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-gray-500">No metrics data for selected host and time range.</p>
      )}
    </div>
  );
}
