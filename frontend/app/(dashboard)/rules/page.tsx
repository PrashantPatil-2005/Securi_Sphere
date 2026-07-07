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
  is_system: boolean;
  rule_type: string;
}

const CORR_TYPES = ["sequence", "co_occurrence", "cross_host"] as const;
const SEVERITIES = ["low", "medium", "high", "critical"] as const;

export default function RulesPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"detection" | "correlation">("detection");
  const [form, setForm] = useState({ name: "", rule_type: "failed_logins", threshold: 5, window_minutes: 5, severity: "high" });
  const [corrForm, setCorrForm] = useState({
    name: "",
    description: "",
    rule_type: "sequence" as (typeof CORR_TYPES)[number],
    event_sequence: "ssh_login_failure,sudo_usage",
    window_minutes: 20,
    min_occurrences: "ssh_login_failure:2",
    severity: "high" as (typeof SEVERITIES)[number],
  });

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

  const corrToggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/correlation-rules/${id}`, { method: "PATCH", body: JSON.stringify({ enabled: !enabled }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["correlation-rules"] }),
  });

  const corrCreateMutation = useMutation({
    mutationFn: () => {
      const min_occurrences: Record<string, number> = {};
      corrForm.min_occurrences.split(",").map((s) => s.trim()).filter(Boolean).forEach((pair) => {
        const [key, val] = pair.split(":").map((x) => x.trim());
        if (key && val) min_occurrences[key] = Number(val);
      });
      return api("/api/v1/correlation-rules", {
        method: "POST",
        body: JSON.stringify({
          name: corrForm.name,
          description: corrForm.description || undefined,
          rule_type: corrForm.rule_type,
          event_sequence: corrForm.event_sequence.split(",").map((s) => s.trim()).filter(Boolean),
          window_minutes: corrForm.window_minutes,
          min_occurrences,
          severity: corrForm.severity,
        }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["correlation-rules"] });
      setCorrForm({
        name: "",
        description: "",
        rule_type: "sequence",
        event_sequence: "ssh_login_failure,sudo_usage",
        window_minutes: 20,
        min_occurrences: "ssh_login_failure:2",
        severity: "high",
      });
      toast("success", "Correlation rule created");
    },
    onError: (e: Error) => toast("error", "Failed", e.message),
  });

  const corrDeleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/correlation-rules/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["correlation-rules"] });
      toast("success", "Correlation rule deleted");
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  const ruleTypes = meta?.supported_rule_types ?? ["failed_logins", "brute_force", "high_cpu", "high_memory", "high_disk", "service_failure", "agent_offline"];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Detection Rules"
        subtitle="Threshold rules and correlation rule visibility"
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
      {tab === "correlation" && (
        <Panel title="Correlation rules" subtitle="System rules are read-only except enable/disable; admins can add custom rules">
          {corrLoading && <TableSkeleton rows={4} />}
          {isError && <QueryError onRetry={() => refetch()} />}
          {!corrLoading && corrRules.length === 0 && (
            <EmptyState title="No correlation rules" description="System rules seed on first startup." />
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              corrCreateMutation.mutate();
            }}
            className="grid md:grid-cols-2 lg:grid-cols-4 gap-3 items-end mb-4"
          >
            <Input required label="Rule name" value={corrForm.name} onChange={(e) => setCorrForm({ ...corrForm, name: e.target.value })} />
            <Select label="Type" value={corrForm.rule_type} onChange={(e) => setCorrForm({ ...corrForm, rule_type: e.target.value as typeof corrForm.rule_type })}>
              {CORR_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </Select>
            <Input required label="Event sequence" hint="Comma-separated" value={corrForm.event_sequence} onChange={(e) => setCorrForm({ ...corrForm, event_sequence: e.target.value })} className="lg:col-span-2" />
            <Input label="Description" value={corrForm.description} onChange={(e) => setCorrForm({ ...corrForm, description: e.target.value })} className="lg:col-span-2" />
            <Input type="number" min={1} label="Window (min)" value={corrForm.window_minutes} onChange={(e) => setCorrForm({ ...corrForm, window_minutes: +e.target.value })} />
            <Input label="Min counts" hint="e.g. ssh_login_failure:3" value={corrForm.min_occurrences} onChange={(e) => setCorrForm({ ...corrForm, min_occurrences: e.target.value })} />
            <Select label="Severity" value={corrForm.severity} onChange={(e) => setCorrForm({ ...corrForm, severity: e.target.value as typeof corrForm.severity })}>
              {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
            <Button type="submit" loading={corrCreateMutation.isPending}>Add rule</Button>
          </form>
          <div className="space-y-2">
            {corrRules.map((r) => (
              <div key={r.id} className="p-3 glass-panel">
                <div className="flex justify-between gap-2 items-start">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{r.name}</span>
                      <span className="text-xs text-accent uppercase">{r.rule_type}</span>
                      <SeverityBadge severity={r.severity} />
                      {r.is_system && <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted/20 text-muted">System</span>}
                    </div>
                    <p className="text-sm text-muted mt-1">{r.description}</p>
                    <p className="text-xs text-muted mt-2 font-mono">{r.event_sequence.join(" → ")} · {r.window_minutes}m · {r.severity}</p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => corrToggleMutation.mutate({ id: r.id, enabled: r.enabled })}
                      className={cn("text-sm px-3 py-1 rounded", r.enabled ? "bg-success/20 text-success" : "bg-muted/20 text-muted")}
                    >
                      {r.enabled ? "Enabled" : "Disabled"}
                    </button>
                    {!r.is_system && (
                      <button
                        type="button"
                        onClick={() => corrDeleteMutation.mutate(r.id)}
                        className="btn-ghost text-sm text-danger"
                        disabled={corrDeleteMutation.isPending}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
