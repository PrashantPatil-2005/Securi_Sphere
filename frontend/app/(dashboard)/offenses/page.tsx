"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";

interface Offense {
  id: string;
  offense_number: number;
  host_name: string;
  title: string;
  risk_level: string;
  status: string;
  event_count: number;
  created_at: string;
}

interface OffenseDetail extends Offense {
  events: { event_type: string; description: string | null; timestamp: string; severity: string }[];
  alerts: { title: string; severity: string; status: string; created_at: string }[];
}

export default function OffensesPage() {
  const { queryParams } = useTimeRange();
  const [offenses, setOffenses] = useState<Offense[]>([]);
  const [selected, setSelected] = useState<OffenseDetail | null>(null);

  const load = () => {
    const q = buildQuery({}, queryParams);
    api<{ items: Offense[] }>(`/api/v1/offenses${q}`).then((r) => setOffenses(r.items)).catch(console.error);
  };

  useEffect(() => { load(); }, [queryParams]);

  const openDetail = (id: string) => {
    api<OffenseDetail>(`/api/v1/offenses/${id}`).then(setSelected).catch(console.error);
  };

  const updateStatus = async (id: string, status: string) => {
    await api(`/api/v1/offenses/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    load();
    if (selected?.id === id) openDetail(id);
  };

  const riskClass = (r: string) =>
    r === "critical" ? "text-red-400" : r === "high" ? "text-orange-400" : r === "medium" ? "text-yellow-400" : "text-gray-400";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Offense Management</h1>
      <p className="text-gray-500 text-sm">QRadar-style correlated security offenses grouped from related alerts and events.</p>
      <TimeRangeBar />

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <h2 className="font-semibold mb-4">Offenses</h2>
          <div className="space-y-2 max-h-[32rem] overflow-y-auto">
            {offenses.map((o) => (
              <button
                key={o.id}
                onClick={() => openDetail(o.id)}
                className={`w-full text-left p-3 rounded border ${selected?.id === o.id ? "border-blue-500 bg-blue-900/20" : "border-[var(--border)] hover:bg-white/5"}`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-mono text-blue-400">#{o.offense_number}</span>
                  <span className={`text-xs uppercase ${riskClass(o.risk_level)}`}>{o.risk_level}</span>
                </div>
                <p className="font-medium mt-1">{o.title}</p>
                <p className="text-xs text-gray-500 mt-1">{o.host_name} · {o.event_count} events · {o.status}</p>
              </button>
            ))}
            {offenses.length === 0 && <p className="text-gray-500">No offenses in selected range.</p>}
          </div>
        </div>

        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          {selected ? (
            <>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="font-semibold">Offense #{selected.offense_number}</h2>
                  <p className="text-sm text-gray-500">Host: {selected.host_name}</p>
                </div>
                <div className="flex gap-2">
                  {(["open", "investigating", "resolved"] as const).map((s) => (
                    <button
                      key={s}
                      onClick={() => updateStatus(selected.id, s)}
                      className={`px-2 py-1 text-xs rounded border ${selected.status === s ? "bg-blue-600 border-blue-500" : "border-[var(--border)]"}`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
              <p className={`text-sm mb-4 ${riskClass(selected.risk_level)}`}>Risk: {selected.risk_level.toUpperCase()}</p>
              <h3 className="text-sm font-semibold mb-2">Events</h3>
              <div className="space-y-1 mb-4 max-h-40 overflow-y-auto text-sm font-mono">
                {selected.events.map((e, i) => (
                  <div key={i} className="flex gap-2 text-gray-400">
                    <span>{new Date(e.timestamp).toLocaleTimeString()}</span>
                    <span>{e.event_type}</span>
                    <span className="truncate">{e.description}</span>
                  </div>
                ))}
              </div>
              <h3 className="text-sm font-semibold mb-2">Alerts</h3>
              <div className="space-y-1 text-sm">
                {selected.alerts.map((a, i) => (
                  <div key={i} className={`severity-${a.severity}`}>{a.title} ({a.status})</div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-gray-500">Select an offense to view details.</p>
          )}
        </div>
      </div>
    </div>
  );
}
