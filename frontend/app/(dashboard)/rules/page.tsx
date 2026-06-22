"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";

interface AlertRule {
  id: string;
  name: string;
  rule_type: string;
  threshold: number | null;
  window_minutes: number | null;
  severity: string;
  enabled: boolean;
}

interface CorrelationRule {
  id: string;
  name: string;
  description: string | null;
  event_sequence: string[];
  window_minutes: number;
  severity: string;
  enabled: boolean;
  rule_type: string;
}

export default function RulesPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"detection" | "correlation">("detection");
  const [form, setForm] = useState({ name: "", rule_type: "failed_logins", threshold: 5, window_minutes: 5, severity: "high" });

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["alert-rules"],
    queryFn: () => api<AlertRule[]>("/api/v1/alert-rules"),
    enabled: tab === "detection",
  });

  const { data: corrRules = [], isLoading: corrLoading, isError, refetch } = useQuery({
    queryKey: ["correlation-rules"],
    queryFn: () => api<CorrelationRule[]>("/api/v1/correlation-rules"),
    enabled: tab === "correlation",
  });

  const { data: meta } = useQuery({
    queryKey: ["alert-rules-meta"],
    queryFn: () => api<{ supported_rule_types: string[] }>("/api/v1/alert-rules/meta"),
    enabled: tab === "detection",
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
      <PageHeader title="Detection Rules" subtitle="Threshold rules and correlation rule visibility" />
      <div className="flex gap-2">
        {(["detection", "correlation"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={cn("btn-ghost capitalize", tab === t && "bg-accent/10 text-accent border-accent/30")}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === "detection" && (
        <>
          {isLoading && <TableSkeleton rows={4} />}
          <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="panel grid md:grid-cols-6 gap-3 items-end">
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input-siem" />
            <select value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })} className="input-siem">
              {ruleTypes.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input type="number" placeholder="Threshold" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: +e.target.value })} className="input-siem" />
            <input type="number" placeholder="Window (min)" value={form.window_minutes} onChange={(e) => setForm({ ...form, window_minutes: +e.target.value })} className="input-siem" />
            <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="input-siem">
              {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <button type="submit" className="btn-primary">Add rule</button>
          </form>
          <div className="space-y-2">
            {rules.map((r) => (
              <div key={r.id} className="flex items-center justify-between p-3 glass-panel">
                <div>
                  <span className="font-medium">{r.name}</span>
                  <span className="text-muted text-sm ml-2">{r.rule_type}</span>
                  <span className={`text-xs ml-2 severity-${r.severity}`}>{r.severity}</span>
                </div>
                <button type="button" onClick={() => toggleMutation.mutate({ id: r.id, enabled: r.enabled })} className={cn("text-sm px-3 py-1 rounded", r.enabled ? "bg-success/20 text-success" : "bg-muted/20 text-muted")}>
                  {r.enabled ? "Enabled" : "Disabled"}
                </button>
              </div>
            ))}
          </div>
        </>
      )}
      {tab === "correlation" && (
        <Panel title="Correlation rules" subtitle="Read-only system rules — sequence, co-occurrence, and cross-host matchers">
          {corrLoading && <TableSkeleton rows={4} />}
          {isError && <QueryError onRetry={() => refetch()} />}
          <div className="space-y-2">
            {corrRules.map((r) => (
              <div key={r.id} className="p-3 glass-panel">
                <div className="flex justify-between gap-2">
                  <span className="font-medium">{r.name}</span>
                  <span className="text-xs text-accent uppercase">{r.rule_type}</span>
                </div>
                <p className="text-sm text-muted mt-1">{r.description}</p>
                <p className="text-xs text-muted mt-2 font-mono">{r.event_sequence.join(" → ")} · {r.window_minutes}m · {r.severity}</p>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
