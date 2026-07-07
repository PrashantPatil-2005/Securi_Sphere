"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";

interface Playbook {
  id: string;
  name: string;
  description: string | null;
  trigger_event: string;
  min_severity: string | null;
  webhook_url: string;
  has_secret: boolean;
  enabled: boolean;
}

interface PlaybookRun {
  id: string;
  trigger_event: string;
  status: string;
  http_status: number | null;
  error_message: string | null;
  created_at: string;
}

const TRIGGERS = [
  "alert_created",
  "offense_created",
  "incident_created",
  "alert_status_changed",
] as const;

const SEVERITIES = ["", "low", "medium", "high", "critical"] as const;

export function PlaybooksPanel({ isAdmin }: { isAdmin: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    trigger_event: "alert_created",
    min_severity: "",
    webhook_url: "",
    webhook_secret: "",
  });

  const { data: playbooks = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["playbooks"],
    queryFn: () => api<Playbook[]>("/api/v1/playbooks"),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api<Playbook>("/api/v1/playbooks", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          description: form.description || null,
          trigger_event: form.trigger_event,
          min_severity: form.min_severity || null,
          webhook_url: form.webhook_url,
          webhook_secret: form.webhook_secret || null,
        }),
      }),
    onSuccess: () => {
      toast("success", "Playbook created");
      setForm({ name: "", description: "", trigger_event: "alert_created", min_severity: "", webhook_url: "", webhook_secret: "" });
      queryClient.invalidateQueries({ queryKey: ["playbooks"] });
    },
    onError: (e: Error) => toast("error", "Create failed", e.message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/playbooks/${id}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["playbooks"] }),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) =>
      api<{ status: string; http_status: number | null; error_message: string | null }>(`/api/v1/playbooks/${id}/test`, {
        method: "POST",
      }),
    onSuccess: (res) => {
      if (res.status === "success") toast("success", "Test webhook delivered", `HTTP ${res.http_status}`);
      else toast("error", "Test failed", res.error_message ?? "Webhook error");
      if (expandedId) queryClient.invalidateQueries({ queryKey: ["playbook-runs", expandedId] });
    },
    onError: (e: Error) => toast("error", "Test failed", e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/playbooks/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("success", "Playbook deleted");
      queryClient.invalidateQueries({ queryKey: ["playbooks"] });
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <Panel title="Create playbook" subtitle="POST JSON webhooks to SOAR tools (PagerDuty, Slack workflows, custom automation)">
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid gap-3 md:grid-cols-2"
        >
          <Input required label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Select label="Trigger" value={form.trigger_event} onChange={(e) => setForm({ ...form, trigger_event: e.target.value })}>
            {TRIGGERS.map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
            ))}
          </Select>
          <Input label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="md:col-span-2" />
          <Select label="Min severity" value={form.min_severity} onChange={(e) => setForm({ ...form, min_severity: e.target.value })}>
            <option value="">Any</option>
            {SEVERITIES.filter(Boolean).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
          <Input
            required
            label="Webhook URL"
            type="url"
            value={form.webhook_url}
            onChange={(e) => setForm({ ...form, webhook_url: e.target.value })}
            placeholder="https://hooks.example.com/soar"
            className="md:col-span-2"
          />
          <Input
            label="Signing secret (optional)"
            type="password"
            value={form.webhook_secret}
            onChange={(e) => setForm({ ...form, webhook_secret: e.target.value })}
            placeholder="HMAC-SHA256 → X-Securi-Signature header"
            className="md:col-span-2"
          />
          <Button type="submit" loading={createMutation.isPending} className="md:col-span-2">Save playbook</Button>
        </form>
      </Panel>

      <Panel title="Playbooks">
        {isLoading ? (
          <TableSkeleton rows={4} />
        ) : playbooks.length === 0 ? (
          <p className="text-sm text-muted">No playbooks yet. Create one to automate webhook responses on alerts, offenses, and incidents.</p>
        ) : (
          <div className="space-y-2">
            {playbooks.map((pb) => (
              <PlaybookRow
                key={pb.id}
                playbook={pb}
                isAdmin={isAdmin}
                expanded={expandedId === pb.id}
                onToggleExpand={() => setExpandedId(expandedId === pb.id ? null : pb.id)}
                onToggleEnabled={(enabled) => toggleMutation.mutate({ id: pb.id, enabled })}
                onTest={() => testMutation.mutate(pb.id)}
                onDelete={() => setPendingDelete({ id: pb.id, name: pb.name })}
                testing={testMutation.isPending}
              />
            ))}
          </div>
        )}
      </Panel>
      <ConfirmDialog
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => {
          if (pendingDelete) deleteMutation.mutate(pendingDelete.id);
          setPendingDelete(null);
        }}
        title="Delete playbook"
        description={pendingDelete ? `Remove "${pendingDelete.name}"? Webhook automation will stop for this playbook.` : ""}
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
      />
    </div>
  );
}

function PlaybookRow({
  playbook: pb,
  isAdmin,
  expanded,
  onToggleExpand,
  onToggleEnabled,
  onTest,
  onDelete,
  testing,
}: {
  playbook: Playbook;
  isAdmin: boolean;
  expanded: boolean;
  onToggleExpand: () => void;
  onToggleEnabled: (enabled: boolean) => void;
  onTest: () => void;
  onDelete: () => void;
  testing: boolean;
}) {
  const { data: runs = [] } = useQuery({
    queryKey: ["playbook-runs", pb.id],
    queryFn: () => api<PlaybookRun[]>(`/api/v1/playbooks/${pb.id}/runs?limit=10`),
    enabled: expanded,
  });

  return (
    <div className="p-3 glass-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium flex items-center gap-2">
            {pb.name}
            <span className={cn("text-[10px] px-1.5 py-0.5 rounded", pb.enabled ? "bg-success/15 text-success" : "bg-muted/20 text-muted")}>
              {pb.enabled ? "enabled" : "disabled"}
            </span>
          </p>
          <p className="text-xs text-muted">
            {pb.trigger_event.replace(/_/g, " ")}
            {pb.min_severity ? ` · ≥ ${pb.min_severity}` : ""}
            {pb.has_secret ? " · signed" : ""}
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          <button type="button" className="btn-ghost text-xs" onClick={onToggleExpand}>
            {expanded ? "Hide runs" : "Runs"}
          </button>
          <button type="button" className="btn-ghost text-xs" onClick={onTest} disabled={testing}>
            Test
          </button>
          <button type="button" className="btn-ghost text-xs" onClick={() => onToggleEnabled(!pb.enabled)}>
            {pb.enabled ? "Disable" : "Enable"}
          </button>
          {isAdmin && (
            <button type="button" className="btn-ghost text-xs text-danger" onClick={onDelete}>
              Delete
            </button>
          )}
        </div>
      </div>
      <p className="text-xs text-muted font-mono truncate mt-1">{pb.webhook_url}</p>
      {expanded && (
        <div className="mt-3 border-t border-border-subtle/50 pt-2 space-y-1">
          {runs.length === 0 ? (
            <p className="text-xs text-muted">No runs yet.</p>
          ) : (
            runs.map((run) => (
              <div key={run.id} className="text-xs flex justify-between gap-2">
                <span className={run.status === "success" ? "text-success" : "text-danger"}>
                  {run.trigger_event} · {run.status}
                  {run.http_status != null ? ` (${run.http_status})` : ""}
                </span>
                <span className="text-muted shrink-0">{new Date(run.created_at).toLocaleString()}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
