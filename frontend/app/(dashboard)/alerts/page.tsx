"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWebSocket } from "@/lib/websocket";

interface Alert {
  id: string;
  host_id: string;
  severity: string;
  title: string;
  description: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export default function AlertsPage() {
  const [tab, setTab] = useState<"open" | "resolved" | "all">("open");
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const load = () => {
    const params = new URLSearchParams();
    if (tab === "open") params.set("status", "open");
    if (tab === "resolved") params.set("status", "resolved");
    api<{ items: Alert[] }>(`/api/v1/alerts?${params}`).then((r) => setAlerts(r.items)).catch(console.error);
  };

  useEffect(() => { load(); }, [tab]);
  useWebSocket((msg) => {
    if (msg.type === "new_alert" || msg.type === "alert_resolved") load();
  });

  async function resolve(id: string) {
    await api(`/api/v1/alerts/${id}/resolve`, { method: "PATCH" });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Alerts</h1>
      <div className="flex gap-2 mb-4">
        {(["open", "resolved", "all"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded text-sm capitalize ${tab === t ? "bg-blue-600" : "bg-[var(--card)] border border-[var(--border)]"}`}>
            {t === "all" ? "History" : t}
          </button>
        ))}
      </div>
      <div className="space-y-3">
        {alerts.map((a) => (
          <div key={a.id} className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <div className="flex justify-between items-start">
              <div>
                <span className={`text-xs uppercase font-bold mr-2 severity-${a.severity}`}>{a.severity}</span>
                <span className="font-medium">{a.title}</span>
                <p className="text-sm text-gray-400 mt-1">{a.description}</p>
                <p className="text-xs text-gray-500 mt-2">{new Date(a.created_at).toLocaleString()}</p>
              </div>
              {a.status === "open" && (
                <button onClick={() => resolve(a.id)} className="text-sm px-3 py-1 bg-green-600/20 text-green-400 rounded hover:bg-green-600/30">
                  Resolve
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      {alerts.length === 0 && <p className="text-gray-500 mt-4">No alerts found.</p>}
    </div>
  );
}
