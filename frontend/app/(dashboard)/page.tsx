"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Overview {
  total_hosts: number;
  online_hosts: number;
  offline_hosts: number;
  active_alerts: number;
  critical_alerts: number;
}

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);

  useEffect(() => {
    api<Overview>("/api/v1/overview").then(setData).catch(console.error);
    const interval = setInterval(() => api<Overview>("/api/v1/overview").then(setData).catch(console.error), 30000);
    return () => clearInterval(interval);
  }, []);

  const cards = [
    { label: "Total Hosts", value: data?.total_hosts ?? "-", color: "text-blue-400" },
    { label: "Online", value: data?.online_hosts ?? "-", color: "text-green-400" },
    { label: "Offline", value: data?.offline_hosts ?? "-", color: "text-gray-400" },
    { label: "Active Alerts", value: data?.active_alerts ?? "-", color: "text-yellow-400" },
    { label: "Critical Alerts", value: data?.critical_alerts ?? "-", color: "text-red-400" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Overview</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <p className="text-sm text-gray-500">{c.label}</p>
            <p className={`text-3xl font-bold ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>
      <p className="mt-8 text-gray-500 text-sm">Security monitoring dashboard for your Linux infrastructure. Data refreshes every 30 seconds.</p>
    </div>
  );
}
