"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
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

export function NotificationSettingsPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["notification-settings"],
    queryFn: () => api<NotifSettings>("/api/v1/notifications/settings"),
  });

  const save = useMutation({
    mutationFn: (body: Partial<NotifSettings>) =>
      api<NotifSettings>("/api/v1/notifications/settings", { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-settings"] });
      toast("success", "Notification settings saved");
    },
    onError: (e: Error) => toast("error", "Save failed", e.message),
  });

  if (isLoading || !data) return null;

  return (
    <Panel title="Delivery channels">
      <div className="space-y-4">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={data.email_enabled} onChange={(e) => save.mutate({ email_enabled: e.target.checked })} />
          <span className="text-body">Email alerts</span>
        </label>
        <Input
          label="Email address"
          value={data.email_address ?? ""}
          onChange={(e) => save.mutate({ email_address: e.target.value })}
        />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={data.slack_enabled} onChange={(e) => save.mutate({ slack_enabled: e.target.checked })} />
          <span className="text-body">Slack webhook</span>
        </label>
        <Input
          label="Slack webhook URL"
          value={data.slack_webhook_url ?? ""}
          onChange={(e) => save.mutate({ slack_webhook_url: e.target.value })}
          placeholder="https://hooks.slack.com/services/..."
        />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={data.telegram_enabled} onChange={(e) => save.mutate({ telegram_enabled: e.target.checked })} />
          <span className="text-body">Telegram</span>
        </label>
        <Input
          label="Telegram chat ID"
          value={data.telegram_chat_id ?? ""}
          onChange={(e) => save.mutate({ telegram_chat_id: e.target.value })}
        />
        <Button onClick={() => toast("success", "All changes auto-saved on edit")}>Done</Button>
      </div>
    </Panel>
  );
}
