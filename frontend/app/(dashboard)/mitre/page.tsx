"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

interface Technique {
  technique_id: string;
  tactic: string;
  name: string;
  count: number;
}

const TACTIC_ORDER = [
  "Initial Access", "Execution", "Persistence", "Privilege Escalation",
  "Defense Evasion", "Discovery", "Lateral Movement", "Credential Access", "Impact",
];

export default function MitrePage() {
  const { queryParams } = useTimeRange();
  const [tactics, setTactics] = useState<Record<string, Technique[]>>({});
  const [stats, setStats] = useState<{ tactic: string; technique_id: string; count: number }[]>([]);

  useEffect(() => {
    const q = buildQuery({}, queryParams);
    api<{ tactics: Record<string, Technique[]> }>(`/api/v1/mitre/matrix${q}`).then((r) => setTactics(r.tactics)).catch(console.error);
    api<{ techniques: { tactic: string; technique_id: string; count: number }[] }>(`/api/v1/siem/mitre${q}`).then((r) => setStats(r.techniques)).catch(console.error);
  }, [queryParams]);

  const tacticOrder = TACTIC_ORDER.filter((t) => tactics[t]).concat(
    Object.keys(tactics).filter((t) => !TACTIC_ORDER.includes(t)),
  );
  const chartData = stats.slice(0, 15).map((t) => ({ name: t.technique_id, count: t.count }));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">MITRE ATT&CK Dashboard</h1>
      <p className="text-gray-500 text-sm mb-4">Map security events to MITRE ATT&CK tactics and techniques</p>
      <TimeRangeBar />

      {chartData.length > 0 && (
        <div className="p-4 mb-6 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <h2 className="font-semibold mb-4">Top Techniques by Event Count</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} layout="vertical">
              <XAxis type="number" stroke="#888" />
              <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 10 }} stroke="#888" />
              <Tooltip contentStyle={{ background: "#1a1a2e", border: "1px solid #333" }} />
              <Bar dataKey="count" fill="#60a5fa" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="overflow-x-auto">
        <div className="flex gap-3 min-w-max pb-4">
          {tacticOrder.map((tactic) => (
            <div key={tactic} className="w-48 shrink-0">
              <div className="bg-blue-900/40 text-blue-300 text-xs font-bold px-2 py-2 rounded-t border border-[var(--border)]">{tactic}</div>
              <div className="border border-t-0 border-[var(--border)] rounded-b min-h-[120px] p-2 space-y-1">
                {(tactics[tactic] || []).map((t) => (
                  <div key={t.technique_id} className={`text-xs p-2 rounded border ${t.count > 0 ? "bg-red-900/30 border-red-800" : "bg-[var(--card)] border-[var(--border)]"}`} title={t.name}>
                    <div className="font-mono text-gray-400">{t.technique_id}</div>
                    <div className="truncate">{t.name}</div>
                    {t.count > 0 && <div className="text-red-400 mt-1">{t.count} events</div>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
