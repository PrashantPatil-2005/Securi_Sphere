"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Trash2, Wrench } from "lucide-react";
import { api } from "@/lib/api";
import { useHostsList, useMaintenanceWindows } from "@/lib/hooks/useApiQuery";
import { useUser } from "@/lib/hooks/useUser";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { HelpTooltip } from "@/components/ui/HelpTooltip";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";

function formatWindowTime(iso: string) {
  return new Date(iso).toLocaleString();
}

function defaultEndsAtLocal() {
  const d = new Date();
  d.setHours(d.getHours() + 1);
  d.setMinutes(0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function MaintenancePage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const formRef = useRef<HTMLDivElement>(null);
  const { data: user } = useUser();
  const canManage = user?.role?.name === "admin" || user?.role?.name === "analyst";
  const { data: hosts = [] } = useHostsList();
  const { data: windows = [], isLoading, isError, refetch } = useMaintenanceWindows();

  const [hostId, setHostId] = useState("");
  const [reason, setReason] = useState("");
  const [endsAt, setEndsAt] = useState(defaultEndsAtLocal);

  useEffect(() => {
    if (!hostId && hosts[0]) setHostId(hosts[0].id);
  }, [hosts, hostId]);

  const createMutation = useMutation({
    mutationFn: () =>
      api("/api/v1/maintenance-windows", {
        method: "POST",
        body: JSON.stringify({
          host_id: hostId,
          reason: reason.trim() || undefined,
          ends_at: new Date(endsAt).toISOString(),
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] });
      setReason("");
      setEndsAt(defaultEndsAtLocal());
      toast("success", "Maintenance window created", "Routine detection alerts are suppressed for this host.");
    },
    onError: (e: Error) => toast("error", "Failed to create window", e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/maintenance-windows/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["maintenance-windows"] });
      toast("success", "Maintenance window removed");
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  function scrollToForm() {
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!hostId) {
      toast("error", "Select a host", "Choose which host is entering maintenance.");
      return;
    }
    createMutation.mutate();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2">
            Maintenance Windows
            <HelpTooltip content="Schedule planned downtime for a host. While a window is active, routine detection alerts (CPU, disk, agent offline, etc.) are suppressed. Correlation and critical paths may still fire." />
          </span>
        }
        subtitle="Suppress routine detection alerts during planned host downtime"
      />

      {!canManage && (
        <div className="px-4 py-3 rounded-lg border border-warning/30 bg-warning/10 text-body text-sm">
          Your account is <strong className="capitalize">{user?.role?.name ?? "viewer"}</strong> — only{" "}
          <strong>admin</strong> or <strong>analyst</strong> can create or remove maintenance windows.
        </div>
      )}

      <Panel title="Upcoming & active windows" subtitle="Windows ending in the past are hidden automatically">
        {isLoading ? (
          <TableSkeleton rows={4} />
        ) : isError ? (
          <QueryError onRetry={() => refetch()} />
        ) : windows.length === 0 ? (
          <EmptyState
            title="No maintenance windows"
            description="Schedule a window when patching, rebooting, or performing planned work on a host."
            icon={<Wrench className="w-10 h-10 opacity-40" />}
            actionLabel={canManage ? "Schedule maintenance" : undefined}
            onAction={canManage ? scrollToForm : undefined}
          />
        ) : (
          <div className="divide-y divide-border-subtle">
            {windows.map((w) => (
              <div key={w.id} className="flex flex-col sm:flex-row sm:items-center gap-3 py-3 first:pt-0 last:pb-0">
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{w.host_name}</span>
                    <span
                      className={cn(
                        "text-[10px] font-medium uppercase tracking-wide px-2 py-0.5 rounded-full",
                        w.active ? "bg-success/15 text-success" : "bg-muted/15 text-muted",
                      )}
                    >
                      {w.active ? "Active" : "Scheduled"}
                    </span>
                  </div>
                  {w.reason && <p className="text-sm text-muted">{w.reason}</p>}
                  <p className="text-xs text-muted tabular-nums">
                    {formatWindowTime(w.starts_at)} → {formatWindowTime(w.ends_at)}
                  </p>
                </div>
                {canManage && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="text-danger shrink-0 self-start sm:self-center"
                    loading={deleteMutation.isPending && deleteMutation.variables === w.id}
                    onClick={() => deleteMutation.mutate(w.id)}
                    aria-label={`Remove maintenance window for ${w.host_name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span className="sr-only sm:not-sr-only sm:ml-1.5">Remove</span>
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>

      {canManage && (
        <div ref={formRef}>
          <Panel title="Schedule maintenance" subtitle="Window starts immediately and ends at the time you choose">
            <form onSubmit={handleCreate} className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
              <Select label="Host" value={hostId} onChange={(e) => setHostId(e.target.value)} required>
                <option value="">Select host…</option>
                {hosts.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name}
                  </option>
                ))}
              </Select>
              <Input
                label="Reason (optional)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. OS patching"
              />
              <Input
                label="Ends at"
                type="datetime-local"
                value={endsAt}
                onChange={(e) => setEndsAt(e.target.value)}
                required
                min={defaultEndsAtLocal()}
                hint="Local time — must be in the future"
              />
              <Button type="submit" loading={createMutation.isPending} className="w-full sm:w-auto">
                <CalendarClock className="w-4 h-4" />
                Create window
              </Button>
            </form>
          </Panel>
        </div>
      )}
    </div>
  );
}
