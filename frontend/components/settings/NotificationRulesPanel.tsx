"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils/cn";

interface NotificationRule {
  id: string;
  name: string;
  trigger_event: string;
  min_severity: string;
  channels: { email: boolean; slack: boolean; telegram: boolean };
  enabled: boolean;
}

const TRIGGERS = [
  { value: "alert_created", label: "New alert" },
  { value: "offense_created", label: "New offense" },
] as const;

const SEVERITIES = ["low", "medium", "high", "critical"] as const;

export function NotificationRulesPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    trigger_event: "alert_created",
    min_severity: "high",
    email: true,
    slack: false,
    telegram: false,
  });

  const { data: rules = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["notification-rules"],
    queryFn: () => api<NotificationRule[]>("/api/v1/notifications/rules"),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api<NotificationRule>("/api/v1/notifications/rules", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          trigger_event: form.trigger_event,
          min_severity: form.min_severity,
          channels: { email: form.email, slack: form.slack, telegram: form.telegram },
        }),
      }),
    onSuccess: () => {
      toast("success", "Notification rule created");
      setForm({ name: "", trigger_event: "alert_created", min_severity: "high", email: true, slack: false, telegram: false });
      queryClient.invalidateQueries({ queryKey: ["notification-rules"] });
    },
    onError: (e: Error) => toast("error", "Create failed", e.message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/notifications/rules/${id}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-rules"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/notifications/rules/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("success", "Rule deleted");
      queryClient.invalidateQueries({ queryKey: ["notification-rules"] });
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) =>
      api<{ channels_sent: string[] }>(`/api/v1/notifications/rules/${id}/test`, { method: "POST" }),
    onSuccess: (res) => {
      if (res.channels_sent.length) toast("success", "Test sent", res.channels_sent.join(", "));
      else toast("warning", "No channels delivered — enable channels in delivery settings");
    },
    onError: (e: Error) => toast("error", "Test failed", e.message),
  });

  if (isLoading) return <TableSkeleton rows={4} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <div className="space-y-6">
      <Panel title="Notification rules" subtitle="Route alerts and offenses to your channels by severity">
        <form
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid gap-3 md:grid-cols-2"
        >
          <Input required label="Rule name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Critical alerts to Slack" />
          <Select label="Trigger" value={form.trigger_event} onChange={(e) => setForm({ ...form, trigger_event: e.target.value })}>
            {TRIGGERS.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </Select>
          <Select label="Min severity" value={form.min_severity} onChange={(e) => setForm({ ...form, min_severity: e.target.value })}>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
          <div className="flex flex-wrap items-end gap-4 md:col-span-2">
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.email} onChange={(e) => setForm({ ...form, email: e.target.checked })} />
              Email
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.slack} onChange={(e) => setForm({ ...form, slack: e.target.checked })} />
              Slack
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.telegram} onChange={(e) => setForm({ ...form, telegram: e.target.checked })} />
              Telegram
            </label>
          </div>
          <Button type="submit" loading={createMutation.isPending} className="md:col-span-2">Add rule</Button>
        </form>
      </Panel>

      <Panel title="Your rules">
        {rules.length === 0 ? (
          <p className="text-sm text-muted">No rules yet. Without rules, high/critical alerts use legacy broadcast to all users with channels enabled.</p>
        ) : (
          <div className="space-y-2">
            {rules.map((rule) => (
              <div key={rule.id} className="p-3 glass-panel flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium flex items-center gap-2">
                    {rule.name}
                    <span className={cn("text-[10px] px-1.5 py-0.5 rounded", rule.enabled ? "bg-success/15 text-success" : "bg-muted/20 text-muted")}>
                      {rule.enabled ? "on" : "off"}
                    </span>
                  </p>
                  <p className="text-xs text-muted capitalize">
                    {rule.trigger_event.replace(/_/g, " ")} · ≥ {rule.min_severity} ·
                    {[rule.channels.email && "email", rule.channels.slack && "slack", rule.channels.telegram && "telegram"].filter(Boolean).join(", ") || "no channels"}
                  </p>
                </div>
                <div className="flex gap-1">
                  <button type="button" className="btn-ghost text-xs" onClick={() => testMutation.mutate(rule.id)} disabled={testMutation.isPending}>
                    Test
                  </button>
                  <button type="button" className="btn-ghost text-xs" onClick={() => toggleMutation.mutate({ id: rule.id, enabled: !rule.enabled })}>
                    {rule.enabled ? "Disable" : "Enable"}
                  </button>
                  <button type="button" className="btn-ghost text-xs text-danger" onClick={() => deleteMutation.mutate(rule.id)}>
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
