"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { CorrelationRuleEditor } from "@/components/rules/CorrelationRuleEditor";
import { RuleFeedbackInsights } from "@/components/rules/RuleFeedbackInsights";
import { useUser } from "@/lib/hooks/useUser";
import { cn } from "@/lib/utils/cn";
import { useToast } from "@/components/ui/Toast";

interface AlertRule {
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
  const { data: user } = useUser();
  const isAdmin = user?.role?.name === "admin";
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"detection" | "correlation">("detection");
  const [form, setForm] = useState({ name: "", rule_type: "failed_logins", threshold: 5, window_minutes: 5, severity: "high" });

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["alert-rules"],
    queryFn: () => api<AlertRule[]>("/api/v1/alert-rules"),
    enabled: tab === "detection",
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
      <PageHeader
        title="Detection Rules"
        subtitle="Threshold detection rules and correlation rule editor"
        action={
          <Link href="/intel" className="btn-ghost text-sm">
            Threat Intel →
          </Link>
        }
      />
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
          <RuleFeedbackInsights />
          <Panel title="Create detection rule" subtitle="Threshold-based alert rules">
            <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="grid md:grid-cols-6 gap-3 items-end">
              <Input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} label="Name" />
              <Select label="Type" value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })}>
                {ruleTypes.map((t) => <option key={t} value={t}>{t}</option>)}
              </Select>
              <Input type="number" label="Threshold" value={form.threshold} onChange={(e) => setForm({ ...form, threshold: +e.target.value })} />
              <Input type="number" label="Window (min)" value={form.window_minutes} onChange={(e) => setForm({ ...form, window_minutes: +e.target.value })} />
              <Select label="Severity" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })}>
                {["low", "medium", "high", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
              </Select>
              <Button type="submit" loading={createMutation.isPending}>Add rule</Button>
            </form>
          </Panel>
          <Panel title="Detection rules" subtitle={isLoading ? "Loading…" : `${rules.length} rule${rules.length === 1 ? "" : "s"}`}>
            {isLoading && <TableSkeleton rows={4} />}
            {!isLoading && rules.length === 0 && (
              <EmptyState title="No detection rules" description="Default rules seed on first startup. Add a custom rule above." />
            )}
            <div className="space-y-2">
              {rules.map((r) => (
                <div key={r.id} className="flex items-center justify-between p-3 glass-panel">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{r.name}</span>
                    <span className="text-muted text-sm">{r.rule_type}</span>
                    <SeverityBadge severity={r.severity} />
                  </div>
                  <button type="button" onClick={() => toggleMutation.mutate({ id: r.id, enabled: r.enabled })} className={cn("text-sm px-3 py-1 rounded", r.enabled ? "bg-success/20 text-success" : "bg-muted/20 text-muted")}>
                    {r.enabled ? "Enabled" : "Disabled"}
                  </button>
                </div>
              ))}
            </div>
          </Panel>
        </>
      )}
      {tab === "correlation" && <CorrelationRuleEditor isAdmin={isAdmin} />}
    </div>
  );
}
