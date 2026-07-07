"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAssistant } from "@/lib/assistant/AssistantProvider";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { InvestigationTrail } from "@/components/InvestigationTrail";
import { WorkspaceNextActions } from "@/components/investigation/WorkspaceNextActions";
import { IocLookupPanel } from "@/components/IocLookupPanel";
import { Panel } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import type { InvestigationWorkspace } from "@/lib/types/investigation";

function buildWorkspaceQuery(params: {
  alertId?: string | null;
  offenseId?: string | null;
  incidentId?: string | null;
}): string | null {
  const qs = new URLSearchParams();
  if (params.alertId) qs.set("alert_id", params.alertId);
  if (params.offenseId) qs.set("offense_id", params.offenseId);
  if (params.incidentId) qs.set("incident_id", params.incidentId);
  const s = qs.toString();
  return s ? `/api/v1/investigation/workspace?${s}` : null;
}

interface Props {
  alertId?: string | null;
  offenseId?: string | null;
  incidentId?: string | null;
}

export function InvestigationWorkspacePane({ alertId, offenseId, incidentId }: Props) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { openWithContext } = useAssistant();

  const path = buildWorkspaceQuery({ alertId, offenseId, incidentId });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["investigation", "workspace", alertId, offenseId, incidentId],
    queryFn: () => api<InvestigationWorkspace>(path!),
    enabled: !!path,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/alerts/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigation"] });
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alerts", "count", "investigating"] });
      queryClient.invalidateQueries({ queryKey: ["alerts", "count", "resolved"] });
      toast("success", "Alert status updated");
    },
  });

  const offenseStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/offenses/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigation"] });
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
    },
  });

  const promoteMutation = useMutation({
    mutationFn: (id: string) =>
      api<{ incident_id: string }>(`/api/v1/offenses/${id}/promote-to-incident`, { method: "POST" }),
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: ["investigation"] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["incidents", "count"] });
      toast("success", "Promoted to incident");
      router.push(workspaceHref({ incidentId: r.incident_id }));
    },
  });

  const noteMutation = useMutation({
    mutationFn: ({ incidentId: incId, content }: { incidentId: string; content: string }) =>
      api(`/api/v1/incidents/${incId}/notes`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigation"] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      toast("success", "Note added");
    },
  });

  if (!path) return null;
  if (isLoading) return <TableSkeleton rows={8} />;
  if (isError) return <QueryError onRetry={() => refetch()} />;
  if (!data) return null;

  const { alert, offense, incident, host, events, timelines, linked_alerts } = data;

  return (
    <div className="space-y-4">
      <InvestigationTrail
        alertId={alert?.id}
        offenseId={offense?.id}
        hostId={host?.id}
        hostName={host?.name}
        incidentId={incident?.id}
      />

      <WorkspaceNextActions
        data={data}
        onPromote={(id) => promoteMutation.mutate(id)}
        promotePending={promoteMutation.isPending}
        onAskAi={() => {
          if (alert) {
            openWithContext({
              alertId: alert.id,
              prefill: "Explain this alert and suggest investigation steps",
            });
          } else if (offense) {
            openWithContext({ offenseId: offense.id });
          }
        }}
      />

      {host && (
        <Panel title="Host context">
          <div className="flex flex-wrap gap-3 text-sm">
            <span className="font-medium">{host.name}</span>
            <span className="text-muted capitalize">{host.status}</span>
            {host.ip_address && <span className="text-muted font-mono">{host.ip_address}</span>}
            {host.risk_score != null && (
              <span className="text-accent tabular-nums">Risk {host.risk_score}</span>
            )}
            <Link href={`/events?host_id=${host.id}`} className="btn-ghost text-xs">
              All events
            </Link>
            <Link href={`/timeline?host=${host.id}`} className="btn-ghost text-xs">
              Timelines
            </Link>
          </div>
        </Panel>
      )}

      {alert && (
        <Panel title="Primary alert">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={alert.severity} />
              <span className="font-semibold">{alert.title}</span>
              <span className="text-xs text-muted capitalize">{alert.status}</span>
            </div>
            {alert.description && <p className="text-sm text-muted">{alert.description}</p>}
            <div className="flex flex-wrap gap-2">
              {alert.status === "open" && (
                <>
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    onClick={() => statusMutation.mutate({ id: alert.id, status: "investigating" })}
                  >
                    Start investigation
                  </button>
                  <button
                    type="button"
                    className="btn-ghost text-xs text-success"
                    onClick={() => statusMutation.mutate({ id: alert.id, status: "resolved" })}
                  >
                    Resolve
                  </button>
                </>
              )}
              <button
                type="button"
                className="btn-ghost text-xs text-accent inline-flex items-center gap-1"
                onClick={() =>
                  openWithContext({
                    alertId: alert.id,
                    prefill: "Explain this alert and suggest investigation steps",
                  })
                }
              >
                <Sparkles className="w-3 h-3" />
                Ask AI
              </button>
            </div>
          </div>
        </Panel>
      )}

      {offense && (
        <Panel title={`Offense #${offense.offense_number}`}>
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={offense.risk_level} />
              <span className="font-medium">{offense.title}</span>
              <span className="text-xs text-muted capitalize">{offense.status}</span>
            </div>
            {offense.description && <p className="text-sm text-muted">{offense.description}</p>}
            <div className="flex flex-wrap gap-2">
              {!offense.incident_id && (
                <button
                  type="button"
                  className="btn-primary text-xs"
                  disabled={promoteMutation.isPending}
                  onClick={() => promoteMutation.mutate(offense.id)}
                >
                  Promote to incident
                </button>
              )}
              {offense.status === "open" && (
                <button
                  type="button"
                  className="btn-ghost text-xs"
                  onClick={() => offenseStatusMutation.mutate({ id: offense.id, status: "investigating" })}
                >
                  Mark investigating
                </button>
              )}
              <button
                type="button"
                className="btn-ghost text-xs text-accent"
                onClick={() => openWithContext({ offenseId: offense.id })}
              >
                Ask AI about offense
              </button>
            </div>
          </div>
        </Panel>
      )}

      {incident && (
        <Panel title="Incident">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge severity={incident.severity} />
              <span className="font-medium">{incident.title}</span>
              <span className="text-xs text-muted capitalize">{incident.status}</span>
            </div>
            {incident.description && <p className="text-sm text-muted">{incident.description}</p>}
            {incident.notes.length > 0 && (
              <ul className="text-sm space-y-2 border-t border-border-subtle pt-3">
                {incident.notes.map((n) => (
                  <li key={n.id} className="text-muted">
                    <span className="text-xs tabular-nums">{new Date(n.created_at).toLocaleString()}</span>
                    <p className="text-foreground mt-0.5">{n.content}</p>
                  </li>
                ))}
              </ul>
            )}
            <IncidentNoteForm
              onSubmit={(content) => noteMutation.mutate({ incidentId: incident.id, content })}
              pending={noteMutation.isPending}
            />
          </div>
        </Panel>
      )}

      {linked_alerts.length > 1 && (
        <Panel title="Linked alerts">
          <ul className="text-sm space-y-2">
            {linked_alerts.map((a) => (
              <li key={a.id}>
                <Link href={workspaceHref({ alertId: a.id })} className="hover:text-accent inline-flex items-center gap-2">
                  <SeverityBadge severity={a.severity} />
                  {a.title}
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {events.length > 0 && (
        <Panel title="Related events">
          <ul className="text-sm font-mono space-y-1 max-h-48 overflow-y-auto">
            {events.map((e) => (
              <li key={e.id} className="flex gap-2 truncate">
                <span className="text-muted shrink-0">{new Date(e.timestamp).toLocaleTimeString()}</span>
                <SeverityBadge severity={e.severity} />
                <span className="truncate">{e.event_type}: {e.description}</span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {timelines.length > 0 && (
        <Panel title="Attack timelines">
          <ul className="text-sm space-y-2">
            {timelines.map((t) => (
              <li key={t.id}>
                <Link href={host ? `/timeline?host=${host.id}` : "/timeline"} className="hover:text-accent">
                  {t.title} — {t.confidence.toFixed(0)}% confidence
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {host?.ip_address && <IocLookupPanel value={host.ip_address} />}
    </div>
  );
}

function IncidentNoteForm({
  onSubmit,
  pending,
}: {
  onSubmit: (content: string) => void;
  pending?: boolean;
}) {
  const [content, setContent] = useState("");

  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!content.trim()) return;
        onSubmit(content.trim());
        setContent("");
      }}
    >
      <input
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Add investigation note…"
        className="input-siem flex-1 text-sm"
      />
      <button type="submit" className="btn-primary text-xs" disabled={pending || !content.trim()}>
        Add note
      </button>
    </form>
  );
}
