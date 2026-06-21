"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";

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
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", rule_type: "failed_logins", threshold: 5, window_minutes: 5, severity: "high" });

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["alert-rules"],
    queryFn: () => api<Rule[]>("/api/v1/alert-rules"),
  });

  const { data: meta } = useQuery({
    queryKey: ["alert-rules-meta"],
    queryFn: () => api<{ supported_rule_types: string[] }>("/api/v1/alert-rules/meta"),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/alert-rules/${id}`, { method: "PATCH", body: JSON.stringify({ enabled: !enabled }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alert-rules"] }),
  });

  const createMutation = useMutation({
    mutationFn: () => api("/api/v1/alert-rules", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
      setForm({ name: "", rule_type: "failed_logins", threshold: 5, window_minutes: 5, severity: "high" });
      toast("success", "Rule created");
    },
    onError: (e: Error) => toast("error", "Failed", e.message),
  });

  const ruleTypes = meta?.supported_rule_types ?? ["failed_logins", "brute_force", "high_cpu", "high_memory", "high_disk", "service_failure", "agent_offline"];

  return (
    <div className="space-y-6">
      <PageHeader title="Detection Rules" subtitle="Supported rule types only — invalid types are rejected by the API" />
      {isLoading && <TableSkeleton rows={4} />}
      <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="mb-6 p-4 panel grid md:grid-cols-6 gap-3 items-end">
        <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm" />
        <select value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })}
          className="px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm">
          {ruleTypes.map((t) => (
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
            <button type="button" onClick={() => toggleMutation.mutate({ id: r.id, enabled: r.enabled })} className={`text-sm px-3 py-1 rounded ${r.enabled ? "bg-success/20 text-success" : "bg-muted/20 text-muted"}`}>
              {r.enabled ? "Enabled" : "Disabled"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
