"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
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
  server_email_configured: boolean;
  server_telegram_configured: boolean;
}

type TestChannel = "email" | "slack" | "telegram";

const emptySettings: NotifSettings = {
  email_enabled: false,
  email_address: "",
  telegram_enabled: false,
  telegram_chat_id: "",
  slack_enabled: false,
  slack_webhook_url: "",
  server_email_configured: false,
  server_telegram_configured: false,
};

function testPayload(form: NotifSettings, channel: TestChannel | "all") {
  const channels =
    channel === "all"
      ? { email: form.email_enabled, slack: form.slack_enabled, telegram: form.telegram_enabled }
      : { email: channel === "email", slack: channel === "slack", telegram: channel === "telegram" };
  return {
    channels,
    email_enabled: form.email_enabled,
    email_address: form.email_address || null,
    slack_enabled: form.slack_enabled,
    slack_webhook_url: form.slack_webhook_url || null,
    telegram_enabled: form.telegram_enabled,
    telegram_chat_id: form.telegram_chat_id || null,
  };
}

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
        server_email_configured: data.server_email_configured,
        server_telegram_configured: data.server_telegram_configured,
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

  const testDelivery = useMutation({
    mutationFn: (channel: TestChannel | "all") =>
      api<{ channels_sent: string[] }>("/api/v1/notifications/settings/test", {
        method: "POST",
        body: JSON.stringify(testPayload(form, channel)),
      }),
    onSuccess: (res) => {
      if (res.channels_sent.length) {
        toast("success", "Test sent", `Delivered: ${res.channels_sent.join(", ")}`);
      } else {
        toast("warning", "No channels delivered", "Enable a channel and fill in its details");
      }
    },
    onError: (e: Error) => toast("error", "Test failed", e.message),
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
        High and critical alerts are forwarded when a channel is enabled and configured. Use test buttons to verify
        delivery without waiting for a real alert.
      </p>
      <div className="mb-4 space-y-2 rounded-lg border border-border-subtle p-3 text-sm">
        <p className="font-medium text-foreground">Server delivery status</p>
        <p className={form.server_email_configured ? "text-success" : "text-muted"}>
          Email SMTP: {form.server_email_configured ? "configured" : "not configured — test logs to server only"}
        </p>
        <p className={form.server_telegram_configured ? "text-success" : "text-muted"}>
          Telegram bot: {form.server_telegram_configured ? "configured" : "not configured — test logs to server only"}
        </p>
        <p className="text-muted">Slack uses your webhook URL below (no server secret required).</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.email_enabled}
              onChange={(e) => setForm((prev) => ({ ...prev, email_enabled: e.target.checked }))}
            />
            <span className="text-body">Email alerts</span>
          </label>
          <div className="flex gap-2 items-end">
            <Input
              label="Email address"
              type="email"
              value={form.email_address ?? ""}
              onChange={(e) => setForm((prev) => ({ ...prev, email_address: e.target.value }))}
              placeholder="you@company.com"
              disabled={!form.email_enabled}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="shrink-0 mb-0.5"
              disabled={!form.email_enabled || !form.email_address || testDelivery.isPending}
              loading={testDelivery.isPending}
              onClick={() => testDelivery.mutate("email")}
            >
              <Send className="w-3.5 h-3.5" />
              Test
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.slack_enabled}
              onChange={(e) => setForm((prev) => ({ ...prev, slack_enabled: e.target.checked }))}
            />
            <span className="text-body">Slack webhook</span>
          </label>
          <div className="flex gap-2 items-end">
            <Input
              label="Slack webhook URL"
              value={form.slack_webhook_url ?? ""}
              onChange={(e) => setForm((prev) => ({ ...prev, slack_webhook_url: e.target.value }))}
              placeholder="https://hooks.slack.com/services/..."
              disabled={!form.slack_enabled}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="shrink-0 mb-0.5"
              disabled={!form.slack_enabled || !form.slack_webhook_url || testDelivery.isPending}
              loading={testDelivery.isPending}
              onClick={() => testDelivery.mutate("slack")}
            >
              <Send className="w-3.5 h-3.5" />
              Test
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={form.telegram_enabled}
              onChange={(e) => setForm((prev) => ({ ...prev, telegram_enabled: e.target.checked }))}
            />
            <span className="text-body">Telegram</span>
          </label>
          <div className="flex gap-2 items-end">
            <Input
              label="Telegram chat ID"
              value={form.telegram_chat_id ?? ""}
              onChange={(e) => setForm((prev) => ({ ...prev, telegram_chat_id: e.target.value }))}
              disabled={!form.telegram_enabled}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="shrink-0 mb-0.5"
              disabled={!form.telegram_enabled || !form.telegram_chat_id || testDelivery.isPending}
              loading={testDelivery.isPending}
              onClick={() => testDelivery.mutate("telegram")}
            >
              <Send className="w-3.5 h-3.5" />
              Test
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <Button type="submit" disabled={save.isPending}>
            Save notification settings
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={testDelivery.isPending || (!form.email_enabled && !form.slack_enabled && !form.telegram_enabled)}
            loading={testDelivery.isPending}
            onClick={() => testDelivery.mutate("all")}
          >
            <Send className="w-4 h-4" />
            Test all enabled
          </Button>
        </div>
      </form>
    </Panel>
  );
}
