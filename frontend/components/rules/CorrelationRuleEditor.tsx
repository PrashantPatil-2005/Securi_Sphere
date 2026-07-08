"use client";

import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, Pencil, Play, Plus, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";

export interface CorrelationRule {
  id: string;
  name: string;
  description: string | null;
  event_sequence: string[];
  window_minutes: number;
  min_occurrences: Record<string, number>;
  severity: string;
  confidence_base: number;
  enabled: boolean;
  is_system: boolean;
  rule_type: string;
}

interface CorrelationMeta {
  rule_types: { id: string; label: string; summary: string }[];
  event_types: string[];
  severities: string[];
  templates: Array<{
    name: string;
    rule_type: string;
    description: string;
    event_sequence: string[];
    window_minutes: number;
    min_occurrences: Record<string, number>;
    severity: string;
    confidence_base: number;
  }>;
}

interface PreviewResult {
  valid: boolean;
  matched: boolean;
  errors?: string[];
  hosts_scanned?: number;
  matches?: Array<{
    host_id: string;
    host_name?: string;
    event_count: number;
    confidence: number;
    event_types?: string[];
  }>;
  event_count?: number;
  confidence?: number;
}

const EMPTY_FORM = {
  name: "",
  description: "",
  rule_type: "sequence",
  event_sequence: ["ssh_login_failure", "sudo_usage"],
  window_minutes: 20,
  min_occurrences: { ssh_login_failure: 2 } as Record<string, number>,
  severity: "high",
  confidence_base: 0.75,
};

function stripDescriptionPrefix(description: string | null) {
  if (!description) return "";
  return description.replace(/^\[(cross_host|co_occurrence)\]\s*/i, "").trim();
}

export function CorrelationRuleEditor({ isAdmin }: { isAdmin: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [minKey, setMinKey] = useState("");
  const [minVal, setMinVal] = useState(2);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);

  const { data: meta } = useQuery({
    queryKey: ["correlation-rules-meta"],
    queryFn: () => api<CorrelationMeta>("/api/v1/correlation-rules/meta"),
  });

  const { data: rules = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["correlation-rules"],
    queryFn: () => api<CorrelationRule[]>("/api/v1/correlation-rules"),
  });

  const payload = useMemo(
    () => ({
      rule_type: form.rule_type,
      event_sequence: form.event_sequence,
      window_minutes: form.window_minutes,
      min_occurrences: form.min_occurrences,
      severity: form.severity,
      confidence_base: form.confidence_base,
    }),
    [form],
  );

  const resetForm = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setPreview(null);
  };

  const loadRule = (rule: CorrelationRule) => {
    setEditingId(rule.id);
    setForm({
      name: rule.name,
      description: stripDescriptionPrefix(rule.description),
      rule_type: rule.rule_type,
      event_sequence: [...rule.event_sequence],
      window_minutes: rule.window_minutes,
      min_occurrences: { ...rule.min_occurrences },
      severity: rule.severity,
      confidence_base: rule.confidence_base,
    });
    setPreview(null);
  };

  const applyTemplate = (templateId: string) => {
    const template = meta?.templates.find((t) => t.name === templateId);
    if (!template) return;
    setForm({
      ...EMPTY_FORM,
      name: template.name,
      description: template.description,
      rule_type: template.rule_type,
      event_sequence: [...template.event_sequence],
      window_minutes: template.window_minutes,
      min_occurrences: { ...template.min_occurrences },
      severity: template.severity,
      confidence_base: template.confidence_base,
    });
    setEditingId(null);
    setPreview(null);
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body = {
        name: form.name,
        description: form.description || undefined,
        ...payload,
      };
      if (editingId) {
        return api<CorrelationRule>(`/api/v1/correlation-rules/${editingId}`, {
          method: "PATCH",
          body: JSON.stringify(body),
        });
      }
      return api<CorrelationRule>("/api/v1/correlation-rules", {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
    onSuccess: () => {
      toast("success", editingId ? "Rule updated" : "Rule created");
      queryClient.invalidateQueries({ queryKey: ["correlation-rules"] });
      resetForm();
    },
    onError: (e: Error) => toast("error", "Save failed", e.message),
  });

  const validateMutation = useMutation({
    mutationFn: () =>
      api<{ valid: boolean; errors: string[] }>("/api/v1/correlation-rules/validate", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (res) => {
      if (res.valid) toast("success", "Rule definition is valid");
      else toast("error", "Validation failed", res.errors.join("; "));
    },
    onError: (e: Error) => toast("error", "Validate failed", e.message),
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      api<PreviewResult>("/api/v1/correlation-rules/preview", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: (res) => {
      setPreview(res);
      if (!res.valid) toast("error", "Invalid rule", res.errors?.join("; "));
    },
    onError: (e: Error) => toast("error", "Preview failed", e.message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/correlation-rules/${id}`, { method: "PATCH", body: JSON.stringify({ enabled: !enabled }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["correlation-rules"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/correlation-rules/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("success", "Rule deleted");
      queryClient.invalidateQueries({ queryKey: ["correlation-rules"] });
      if (pendingDelete && editingId === pendingDelete.id) resetForm();
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  const moveEvent = (index: number, direction: -1 | 1) => {
    const next = [...form.event_sequence];
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    setForm({ ...form, event_sequence: next });
  };

  const eventTypes = meta?.event_types ?? ["ssh_login_failure", "ssh_login_success", "sudo_usage"];

  return (
    <div className="space-y-6">
      <Panel
        title={editingId ? "Edit correlation rule" : "Create correlation rule"}
        subtitle="Sequence, co-occurrence, and cross-host matchers with live preview"
      >
        {!isAdmin && (
          <p className="text-sm text-muted mb-4">Analysts can validate and preview rules. Only admins can save changes.</p>
        )}
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            if (!isAdmin) return;
            saveMutation.mutate();
          }}
          className="space-y-4"
        >
          <div className="flex flex-wrap gap-3 items-end">
            {meta?.templates?.length ? (
              <Select
                label="Template"
                value=""
                onChange={(e) => e.target.value && applyTemplate(e.target.value)}
                className="min-w-[220px]"
              >
                <option value="">Load template…</option>
                {meta.templates.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </Select>
            ) : null}
            {editingId ? (
              <Button type="button" variant="ghost" onClick={resetForm}>
                <X className="w-4 h-4 mr-1" /> Cancel edit
              </Button>
            ) : null}
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
            <Input required label="Rule name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} disabled={!isAdmin} />
            <Select label="Type" value={form.rule_type} onChange={(e) => setForm({ ...form, rule_type: e.target.value })} disabled={!isAdmin}>
              {(meta?.rule_types ?? [{ id: "sequence", label: "Sequence" }]).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </Select>
            <Input type="number" min={1} max={1440} label="Window (min)" value={form.window_minutes} onChange={(e) => setForm({ ...form, window_minutes: +e.target.value })} disabled={!isAdmin} />
            <Select label="Severity" value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} disabled={!isAdmin}>
              {(meta?.severities ?? ["low", "medium", "high", "critical"]).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
            <Input label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="lg:col-span-2" disabled={!isAdmin} />
            <Input
              type="number"
              min={0}
              max={1}
              step={0.05}
              label="Confidence base"
              value={form.confidence_base}
              onChange={(e) => setForm({ ...form, confidence_base: +e.target.value })}
              disabled={!isAdmin}
            />
          </div>

          {meta?.rule_types?.find((t) => t.id === form.rule_type)?.summary ? (
            <p className="text-xs text-muted">{meta.rule_types.find((t) => t.id === form.rule_type)?.summary}</p>
          ) : null}

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Event sequence</span>
              {isAdmin ? (
                <Button
                  type="button"
                  variant="ghost"
                  className="text-xs"
                  onClick={() => setForm({ ...form, event_sequence: [...form.event_sequence, eventTypes[0] ?? "ssh_login_failure"] })}
                >
                  <Plus className="w-3 h-3 mr-1" /> Add step
                </Button>
              ) : null}
            </div>
            <div className="space-y-2">
              {form.event_sequence.map((etype, index) => (
                <div key={`${etype}-${index}`} className="flex flex-wrap items-center gap-2 p-2 rounded-lg border border-border-subtle">
                  <span className="text-xs text-muted w-6">{index + 1}</span>
                  <Select
                    value={etype}
                    onChange={(e) => {
                      const next = [...form.event_sequence];
                      next[index] = e.target.value;
                      setForm({ ...form, event_sequence: next });
                    }}
                    className="flex-1 min-w-[180px]"
                    disabled={!isAdmin}
                  >
                    {eventTypes.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </Select>
                  {isAdmin ? (
                    <>
                      <button type="button" className="btn-ghost p-1" disabled={index === 0} onClick={() => moveEvent(index, -1)} aria-label="Move up">
                        <ChevronUp className="w-4 h-4" />
                      </button>
                      <button type="button" className="btn-ghost p-1" disabled={index === form.event_sequence.length - 1} onClick={() => moveEvent(index, 1)} aria-label="Move down">
                        <ChevronDown className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        className="btn-ghost p-1 text-danger"
                        disabled={form.event_sequence.length <= 1}
                        onClick={() => setForm({ ...form, event_sequence: form.event_sequence.filter((_, i) => i !== index) })}
                        aria-label="Remove step"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <span className="text-sm font-medium">Minimum occurrences</span>
            <div className="flex flex-wrap gap-2 items-end">
              <Select label="Event / key" value={minKey} onChange={(e) => setMinKey(e.target.value)} className="min-w-[180px]" disabled={!isAdmin}>
                <option value="">Select…</option>
                {form.rule_type === "cross_host" ? <option value="hosts">hosts</option> : null}
                {eventTypes.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
              <Input type="number" min={1} label="Count" value={minVal} onChange={(e) => setMinVal(+e.target.value)} className="w-24" disabled={!isAdmin} />
              {isAdmin ? (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    if (!minKey) return;
                    setForm({ ...form, min_occurrences: { ...form.min_occurrences, [minKey]: minVal } });
                    setMinKey("");
                  }}
                >
                  Add
                </Button>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.entries(form.min_occurrences).map(([key, val]) => (
                <span key={key} className="text-xs px-2 py-1 rounded bg-muted/20 font-mono flex items-center gap-1">
                  {key}:{val}
                  {isAdmin ? (
                    <button
                      type="button"
                      className="text-danger"
                      onClick={() => {
                        const next = { ...form.min_occurrences };
                        delete next[key];
                        setForm({ ...form, min_occurrences: next });
                      }}
                    >
                      ×
                    </button>
                  ) : null}
                </span>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="ghost" onClick={() => validateMutation.mutate()} loading={validateMutation.isPending}>
              Validate
            </Button>
            <Button type="button" variant="ghost" onClick={() => previewMutation.mutate()} loading={previewMutation.isPending}>
              <Play className="w-4 h-4 mr-1" /> Preview
            </Button>
            {isAdmin ? (
              <Button type="submit" loading={saveMutation.isPending}>
                {editingId ? "Save changes" : "Create rule"}
              </Button>
            ) : null}
          </div>

          {preview ? (
            <div className="text-sm p-3 rounded-lg border border-border-subtle bg-[var(--sidebar-hover)]/20">
              <p className="font-medium mb-1">{preview.matched ? "Would match now" : "No current matches"}</p>
              {preview.errors?.length ? <p className="text-danger text-xs">{preview.errors.join("; ")}</p> : null}
              {preview.matches?.length ? (
                <ul className="text-xs text-muted mt-2 space-y-1">
                  {preview.matches.map((m) => (
                    <li key={m.host_id}>
                      {m.host_name ?? m.host_id}: {m.event_count} events · confidence {m.confidence}
                    </li>
                  ))}
                </ul>
              ) : null}
              {preview.event_count != null ? (
                <p className="text-xs text-muted mt-1">
                  {preview.event_count} events · confidence {preview.confidence}
                </p>
              ) : null}
              {preview.hosts_scanned != null ? <p className="text-xs text-muted">Scanned {preview.hosts_scanned} hosts</p> : null}
            </div>
          ) : null}
        </form>
      </Panel>

      <Panel title="Correlation rules" subtitle={isLoading ? "Loading…" : `${rules.length} rules`}>
        {isLoading && <TableSkeleton rows={4} />}
        {isError && <QueryError onRetry={() => refetch()} />}
        {!isLoading && rules.length === 0 && (
          <EmptyState title="No correlation rules" description="System rules seed on first startup." />
        )}
        <div className="space-y-2">
          {rules.map((r) => (
            <div key={r.id} className={cn("p-3 glass-panel", editingId === r.id && "ring-1 ring-accent/40")}>
              <div className="flex justify-between gap-2 items-start">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{r.name}</span>
                    <span className="text-xs text-accent uppercase">{r.rule_type}</span>
                    <SeverityBadge severity={r.severity} />
                    {r.is_system ? (
                      <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted/20 text-muted">System</span>
                    ) : null}
                  </div>
                  <p className="text-sm text-muted mt-1">{stripDescriptionPrefix(r.description)}</p>
                  <p className="text-xs text-muted mt-2 font-mono">
                    {r.event_sequence.join(r.rule_type === "co_occurrence" ? " + " : " → ")} · {r.window_minutes}m
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  {isAdmin && !r.is_system ? (
                    <button type="button" className="btn-ghost text-sm" onClick={() => loadRule(r)}>
                      <Pencil className="w-3.5 h-3.5 mr-1" /> Edit
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => toggleMutation.mutate({ id: r.id, enabled: r.enabled })}
                    className={cn("text-sm px-3 py-1 rounded", r.enabled ? "bg-success/20 text-success" : "bg-muted/20 text-muted")}
                    disabled={!isAdmin}
                  >
                    {r.enabled ? "Enabled" : "Disabled"}
                  </button>
                  {isAdmin && !r.is_system ? (
                    <button type="button" onClick={() => setPendingDelete({ id: r.id, name: r.name })} className="btn-ghost text-sm text-danger">
                      Delete
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <ConfirmDialog
        open={!!pendingDelete}
        title="Delete correlation rule?"
        description={pendingDelete ? `Remove "${pendingDelete.name}" permanently.` : ""}
        confirmLabel="Delete"
        danger
        onConfirm={() => {
          if (pendingDelete) deleteMutation.mutate(pendingDelete.id);
          setPendingDelete(null);
        }}
        onClose={() => setPendingDelete(null)}
      />
    </div>
  );
}
