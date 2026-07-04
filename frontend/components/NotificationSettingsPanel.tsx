"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";

interface NotifSettings {
  email_enabled: boolean;
  email_address: string | null;
  telegram_enabled: boolean;
  telegram_chat_id: string | null;
  slack_enabled: boolean;
  slack_webhook_url: string | null;
}

const emptySettings: NotifSettings = {
  email_enabled: false,
  email_address: "",
  telegram_enabled: false,
  telegram_chat_id: "",
  slack_enabled: false,
  slack_webhook_url: "",
};

export function NotificationSettingsPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<NotifSettings>(emptySettings);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["notification-settings"],
    queryFn: () => api<NotifSettings>("/api/v1/notifications/settings"),
  });

  useEffect(() => {
    if (data) {
      setForm({
        email_enabled: data.email_enabled,
        email_address: data.email_address ?? "",
        telegram_enabled: data.telegram_enabled,
        telegram_chat_id: data.telegram_chat_id ?? "",
        slack_enabled: data.slack_enabled,
        slack_webhook_url: data.slack_webhook_url ?? "",
      });
    }
  }, [data]);

  const save = useMutation({
    mutationFn: () =>
      api<NotifSettings>("/api/v1/notifications/settings", { method: "PATCH", body: JSON.stringify(form) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-settings"] });
      toast("success", "Notification settings saved");
    },
    onError: (e: Error) => toast("error", "Save failed", e.message),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  if (isLoading) return <TableSkeleton rows={6} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <Panel title="Delivery channels">
      <p className="text-caption normal-case text-muted mb-4">
        High and critical alerts are forwarded when a channel is enabled and configured.
      </p>
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.email_enabled}
            onChange={(e) => setForm((prev) => ({ ...prev, email_enabled: e.target.checked }))}
          />
          <span className="text-body">Email alerts</span>
        </label>
        <Input
          label="Email address"
          type="email"
          value={form.email_address ?? ""}
          onChange={(e) => setForm((prev) => ({ ...prev, email_address: e.target.value }))}
          placeholder="you@company.com"
          disabled={!form.email_enabled}
        />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.slack_enabled}
            onChange={(e) => setForm((prev) => ({ ...prev, slack_enabled: e.target.checked }))}
          />
          <span className="text-body">Slack webhook</span>
        </label>
        <Input
          label="Slack webhook URL"
          value={form.slack_webhook_url ?? ""}
          onChange={(e) => setForm((prev) => ({ ...prev, slack_webhook_url: e.target.value }))}
          placeholder="https://hooks.slack.com/services/..."
          disabled={!form.slack_enabled}
        />
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.telegram_enabled}
            onChange={(e) => setForm((prev) => ({ ...prev, telegram_enabled: e.target.checked }))}
          />
          <span className="text-body">Telegram</span>
        </label>
        <Input
          label="Telegram chat ID"
          value={form.telegram_chat_id ?? ""}
          onChange={(e) => setForm((prev) => ({ ...prev, telegram_chat_id: e.target.value }))}
          disabled={!form.telegram_enabled}
        />
        <Button type="submit" disabled={save.isPending}>
          Save notification settings
        </Button>
      </form>
    </Panel>
  );
}
