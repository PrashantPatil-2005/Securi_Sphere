"use client";

import { useEffect, useState } from "react";
import { API_URL, api } from "@/lib/api";

interface Summary {
  total_hosts: number;
  open_alerts: number;
  threat_scores: { host_id: string; score: number }[];
}

export default function ReportsPage() {
  const [data, setData] = useState<Summary | null>(null);

  useEffect(() => {
    api<Summary>("/api/v1/reports/summary").then(setData).catch(console.error);
  }, []);

  async function downloadCsv() {
    const token = localStorage.getItem("access_token");
    const res = await fetch(`${API_URL}/api/v1/reports/summary?format=csv`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "threat-scores.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reports</h1>
      {data && (
        <div className="grid md:grid-cols-3 gap-4 mb-6">
          <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <p className="text-gray-500 text-sm">Total Hosts</p>
            <p className="text-2xl font-bold">{data.total_hosts}</p>
          </div>
          <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <p className="text-gray-500 text-sm">Open Alerts</p>
            <p className="text-2xl font-bold text-yellow-400">{data.open_alerts}</p>
          </div>
          <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <p className="text-gray-500 text-sm">Hosts Scored</p>
            <p className="text-2xl font-bold">{data.threat_scores.length}</p>
          </div>
        </div>
      )}
      <button onClick={downloadCsv} className="px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-500">
        Export Threat Scores (CSV)
      </button>
      {data && data.threat_scores.length > 0 && (
        <div className="mt-6 p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <h2 className="font-semibold mb-3">Threat Scores</h2>
          {data.threat_scores.map((s) => (
            <div key={s.host_id} className="flex justify-between text-sm py-1 border-b border-[var(--border)]/50">
              <span className="font-mono text-gray-400">{s.host_id.slice(0, 8)}...</span>
              <span>{s.score}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
