"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Rule {
  id: string;
  name: string;
  rule_type: string;
  threshold: number | null;
  window_minutes: number | null;
  severity: string;
  enabled: boolean;
}

export default function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [form, setForm] = useState({ name: "", rule_type: "failed_logins", threshold: 5, window_minutes: 5, severity: "high" });

  const load = () => api<Rule[]>("/api/v1/alert-rules").then(setRules).catch(console.error);
  useEffect(() => { load(); }, []);

  async function toggle(id: string, enabled: boolean) {
    await api(`/api/v1/alert-rules/${id}`, { method: "PATCH", body: JSON.stringify({ enabled: !enabled }) });
    load();
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/alert-rules", { method: "POST", body: JSON.stringify(form) });
    setForm({ name: "", rule_type: "failed_logins", threshold: 5, window_minutes: 5, severity: "high" });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Detection Rules</h1>
      <form onSubmit={create} className="mb-6 p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg grid md:grid-cols-6 gap-3 items-end">
        <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm" />
        <select value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })}
          className="px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm">
          {["failed_logins", "brute_force", "high_cpu", "high_memory", "high_disk", "service_failure", "agent_offline"].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <input type="number" placeholder="Threshold" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: +e.target.value })}
          className="px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm" />
        <input type="number" placeholder="Window (min)" value={form.window_minutes} onChange={(e) => setForm({ ...form, window_minutes: +e.target.value })}
          className="px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm" />
        <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}
          className="px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm">
          {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <button type="submit" className="px-4 py-2 bg-blue-600 rounded text-sm hover:bg-blue-500">Add Rule</button>
      </form>
      <div className="space-y-2">
        {rules.map((r) => (
          <div key={r.id} className="flex items-center justify-between p-3 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <div>
              <span className="font-medium">{r.name}</span>
              <span className="text-gray-500 text-sm ml-2">{r.rule_type}</span>
              <span className={`text-xs ml-2 severity-${r.severity}`}>{r.severity}</span>
            </div>
            <button onClick={() => toggle(r.id, r.enabled)} className={`text-sm px-3 py-1 rounded ${r.enabled ? "bg-green-900/30 text-green-400" : "bg-gray-800 text-gray-500"}`}>
              {r.enabled ? "Enabled" : "Disabled"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
