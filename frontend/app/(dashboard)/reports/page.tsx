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
  const [reportType, setReportType] = useState<"daily" | "weekly" | "monthly">("daily");

  useEffect(() => {
    api<Summary>("/api/v1/reports/summary").then(setData).catch(console.error);
  }, []);

  async function download(format: "csv" | "pdf") {
    const token = localStorage.getItem("access_token");
    const res = await fetch(`${API_URL}/api/v1/reports/generate?report_type=${reportType}&format=${format}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `securisphere_${reportType}_report.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Security Reports</h1>
      <p className="text-gray-500 text-sm mb-6">Generate daily, weekly, or monthly reports with events, alerts, risk scores, MITRE mapping, and attack timelines.</p>
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
      <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg space-y-4">
        <div className="flex flex-wrap gap-3 items-center">
          <label className="text-sm text-gray-500">Report Period</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value as typeof reportType)} className="px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm">
            <option value="daily">Daily Report</option>
            <option value="weekly">Weekly Report</option>
            <option value="monthly">Monthly Report</option>
          </select>
        </div>
        <div className="flex gap-3">
          <button onClick={() => download("pdf")} className="px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-500">Export PDF</button>
          <button onClick={() => download("csv")} className="px-4 py-2 border border-[var(--border)] rounded text-sm hover:bg-white/5">Export CSV</button>
        </div>
        <p className="text-xs text-gray-500">Reports include: total events, alerts, top hosts, risk scores, attack timelines, and MITRE technique mapping.</p>
      </div>
    </div>
  );
}
