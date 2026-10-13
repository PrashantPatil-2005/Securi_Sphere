"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { AlertTriangle, RotateCcw, Sparkles } from "lucide-react";
import { api, errorStatus } from "@/lib/api";
import { useAssistant } from "@/lib/assistant/AssistantProvider";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { useUser } from "@/lib/hooks/useUser";
import { InvestigationTrail } from "@/components/InvestigationTrail";
import { WorkspaceNextActions } from "@/components/investigation/WorkspaceNextActions";
import { IocLookupPanel } from "@/components/IocLookupPanel";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import type { InvestigationWorkspace, WorkspaceTimelineEntry } from "@/lib/types/investigation";

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

const TIMELINE_TYPE_LABELS: Record<WorkspaceTimelineEntry["type"], string> = {
  incident: "Incident",
  alert: "Alert",
  offense: "Offense",
  event: "Event",
  note: "Note",
  timeline: "Timeline",
};

export function InvestigationWorkspacePane({ alertId, offenseId, incidentId }: Props) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { openWithContext } = useAssistant();
  const { data: currentUser } = useUser();

  const path = buildWorkspaceQuery({ alertId, offenseId, incidentId });

  const { data, isLoading, isError, error, isFetching, refetch } = useQuery({
    queryKey: ["investigation", "workspace", alertId, offenseId, incidentId],
    queryFn: () => api<InvestigationWorkspace>(path!),
    enabled: !!path,
    retry: (failureCount, err) => {
      const status = errorStatus(err);
      // 401/403/404 are deterministic — retrying only delays the state the user must see.
      if (status && [400, 401, 403, 404].includes(status)) return false;
      return failureCount < 1;
    },
  });

  // Developer diagnostics only — never surfaces secrets or raw server internals in the UI.
  useEffect(() => {
    if (!isError) return;
    console.error("[case-workspace] failed to load", {
      path,
      status: errorStatus(error),
      detail: error instanceof Error ? error.message : String(error),
    });
  }, [isError, error, path]);

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

  const incidentStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/incidents/${id}/status?status=${encodeURIComponent(status)}`, {
        method: "PATCH",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigation"] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      toast("success", "Incident status updated");
    },
    onError: (err) => {
      const status = errorStatus(err);
      toast("error", status === 403 ? "Your role cannot change incident status" : "Failed to update incident status");
    },
  });

  const incidentAssignMutation = useMutation({
    mutationFn: ({ id, assignedTo }: { id: string; assignedTo: string | null }) =>
      api(`/api/v1/incidents/${id}/assign`, {
        method: "PATCH",
        body: JSON.stringify({ assigned_to: assignedTo }),
      }),
    onSuccess: (_r, vars) => {
      queryClient.invalidateQueries({ queryKey: ["investigation"] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      toast("success", vars.assignedTo ? "Incident assigned" : "Assignment cleared");
    },
    onError: (err) => {
      const status = errorStatus(err);
      toast("error", status === 403 ? "Your role cannot assign incidents" : "Failed to update assignment");
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

  if (isError) {
    const status = errorStatus(error);
    const detail = error instanceof Error ? error.message : undefined;

    if (status === 404) {
      return (
        <Panel title="Case not found">
          <EmptyState
            title="This case is no longer available"
            description={
              detail ||
              "The incident, offense, or alert you opened does not exist, or it was removed."
            }
          />
          <div className="flex flex-wrap gap-2 mt-4">
            <Link href="/incidents" className="btn-ghost text-sm">Browse incidents</Link>
            <Link href="/alerts" className="btn-ghost text-sm">Browse alerts</Link>
            <Link href="/offenses" className="btn-ghost text-sm">Browse offenses</Link>
          </div>
        </Panel>
      );
    }

    if (status === 401 || status === 403) {
      return (
        <QueryError
          message="You do not have access to this case"
          description="Your current role cannot open this case. Sign in with an analyst or admin account, or ask an administrator for access."
          onRetry={() => refetch()}
          retrying={isFetching}
        />
      );
    }

    const unreachable = status === 0 || (status != null && status >= 500);
    return (
      <QueryError
        message={unreachable ? "Case data could not be loaded" : "Failed to load case data"}
        description={
          unreachable
            ? "The backend did not complete the request. Check your connection, then retry — the same request will be sent again."
            : detail || "Something went wrong while loading this case."
        }
        onRetry={() => refetch()}
        retrying={isFetching}
      />
    );
  }
  if (!data) return null;

  const { alert, offense, incident, host, events, timelines, linked_alerts } = data;
  const investigationTimeline = data.investigation_timeline ?? [];
  const entities = data.entities ?? { hosts: [], accounts: [], network_ips: [] };
  const mitre = data.mitre ?? { technique_ids: [], tactics: [] };
  const provenance = data.provenance ?? { simulated: false, sources: [] };
  const partialErrors = data.partial_errors ?? [];

  const hasCaseContent =
    !!(alert || offense || incident || host) ||
    events.length > 0 ||
    timelines.length > 0 ||
    investigationTimeline.length > 0;
  if (!hasCaseContent) {
    return (
      <Panel title="Empty case">
        <EmptyState
          title="No data linked to this case"
          description="This record exists, but no alerts, offenses, host context, events, or timelines are linked to it yet."
        />
      </Panel>
    );
  }

  const role = currentUser?.role?.name;
  const canActOnIncident =
    !!incident && !!currentUser && (role === "analyst" || role === "admin");
  const assignedToMe = !!incident?.assigned_to && incident.assigned_to === currentUser?.id;

  return (
    <div className="space-y-4">
      <InvestigationTrail
        alertId={alert?.id}
        offenseId={offense?.id}
        hostId={host?.id}
        hostName={host?.name}
        incidentId={incident?.id}
      />

      {isFetching && (
        <p className="text-xs text-muted" role="status" aria-live="polite">
          Refreshing case data…
        </p>
      )}

      {provenance.simulated && (
        <div
          role="status"
          className="flex items-start gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200"
        >
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" aria-hidden />
          <span>
            Synthetic demo data — generated by the Demo Center, not live telemetry.
            {provenance.sources.length > 0 && (
              <> Sources: {provenance.sources.join(", ")}.</>
            )}
          </span>
        </div>
      )}

      {partialErrors.length > 0 && (
        <div
          role="alert"
          className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200"
        >
          <div className="flex items-start justify-between gap-3">
            <span>
              Some case data could not be loaded: {partialErrors.join(", ")}.
              What is shown may be incomplete.
            </span>
            <button
              type="button"
              className="btn-ghost text-xs shrink-0 inline-flex items-center gap-1"
              disabled={isFetching}
              onClick={() => refetch()}
            >
              <RotateCcw className="w-3 h-3" aria-hidden />
              Retry
            </button>
          </div>
        </div>
      )}

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
              {alert.source === "simulation" && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-200 border border-amber-500/40">
                  SIMULATED
                </span>
              )}
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
              {incident.simulated && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-200 border border-amber-500/40">
                  SIMULATED
                </span>
              )}
            </div>
            {incident.description && <p className="text-sm text-muted">{incident.description}</p>}
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
              <span>
                Assignee:{" "}
                <span className="text-foreground">
                  {incident.assignee_email || "Unassigned"}
                </span>
              </span>
              {incident.confidence != null && incident.confidence > 0 && (
                <span>Confidence {(incident.confidence * 100).toFixed(0)}%</span>
              )}
              {incident.first_observed && (
                <span>First observed {new Date(incident.first_observed).toLocaleString()}</span>
              )}
              {incident.last_observed && (
                <span>Last observed {new Date(incident.last_observed).toLocaleString()}</span>
              )}
              <Link href={`/incidents/${incident.id}`} className="btn-ghost text-xs">
                Incident detail
              </Link>
            </div>
            {canActOnIncident && (
              <div className="flex flex-wrap items-center gap-2 border-t border-border-subtle pt-3">
                {incident.status === "open" && (
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    disabled={incidentStatusMutation.isPending}
                    onClick={() => incidentStatusMutation.mutate({ id: incident.id, status: "investigating" })}
                  >
                    Start investigating
                  </button>
                )}
                {(incident.status === "open" || incident.status === "investigating") && (
                  <button
                    type="button"
                    className="btn-ghost text-xs text-success"
                    disabled={incidentStatusMutation.isPending}
                    onClick={() => incidentStatusMutation.mutate({ id: incident.id, status: "resolved" })}
                  >
                    Resolve
                  </button>
                )}
                {incident.status === "resolved" && (
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    disabled={incidentStatusMutation.isPending}
                    onClick={() => incidentStatusMutation.mutate({ id: incident.id, status: "closed" })}
                  >
                    Close
                  </button>
                )}
                {(incident.status === "resolved" || incident.status === "closed") && (
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    disabled={incidentStatusMutation.isPending}
                    onClick={() => incidentStatusMutation.mutate({ id: incident.id, status: "investigating" })}
                  >
                    Reopen
                  </button>
                )}
                {!assignedToMe && (
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    disabled={incidentAssignMutation.isPending || !currentUser}
                    onClick={() =>
                      currentUser &&
                      incidentAssignMutation.mutate({ id: incident.id, assignedTo: currentUser.id })
                    }
                  >
                    Assign to me
                  </button>
                )}
                {incident.assigned_to && (
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    disabled={incidentAssignMutation.isPending}
                    onClick={() => incidentAssignMutation.mutate({ id: incident.id, assignedTo: null })}
                  >
                    Unassign
                  </button>
                )}
              </div>
            )}
            {incident.notes.length > 0 && (
              <ul className="text-sm space-y-2 border-t border-border-subtle pt-3">
                {incident.notes.map((n) => (
                  <li key={n.id} className="text-muted">
                    <span className="text-xs tabular-nums">{new Date(n.created_at).toLocaleString()}</span>
                    {n.user_email && <span className="text-xs"> — {n.user_email}</span>}
                    <p className="text-foreground mt-0.5">{n.content}</p>
                  </li>
                ))}
              </ul>
            )}
            <IncidentNoteForm
              onSubmit={(content) => noteMutation.mutate({ incidentId: incident.id, content })}
              pending={noteMutation.isPending}
              disabled={!canActOnIncident}
            />
          </div>
        </Panel>
      )}

      {(mitre.technique_ids.length > 0 || mitre.tactics.length > 0) && (
        <Panel title="MITRE ATT&CK">
          <div className="space-y-2">
            {mitre.technique_ids.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-xs text-muted">Techniques:</span>
                {mitre.technique_ids.map((t) => (
                  <Link
                    key={t}
                    href="/mitre"
                    className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20 hover:border-accent/50"
                  >
                    {t}
                  </Link>
                ))}
              </div>
            )}
            {mitre.tactics.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-xs text-muted">Tactics:</span>
                {mitre.tactics.map((t) => (
                  <span
                    key={t}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-muted/40 text-muted border border-border-subtle capitalize"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        </Panel>
      )}

      {(entities.hosts.length > 0 || entities.accounts.length > 0 || entities.network_ips.length > 0) && (
        <Panel title="Entities">
          <div className="space-y-2 text-sm">
            {entities.hosts.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted">Hosts:</span>
                {entities.hosts.map((h) =>
                  h.id ? (
                    <Link key={h.id} href={`/hosts/${h.id}`} className="hover:text-accent">
                      {h.name}
                      {h.ip && <span className="text-muted font-mono"> ({h.ip})</span>}
                    </Link>
                  ) : (
                    <span key={h.name} className="text-muted">{h.name}</span>
                  ),
                )}
              </div>
            )}
            {entities.accounts.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted">Accounts:</span>
                {entities.accounts.map((a) => (
                  <span key={a} className="font-mono text-xs">{a}</span>
                ))}
              </div>
            )}
            {entities.network_ips.length > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted">Network IPs:</span>
                {entities.network_ips.map((ip) => (
                  <span key={ip} className="font-mono text-xs">{ip}</span>
                ))}
              </div>
            )}
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
                  {a.source === "simulation" && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-200 border border-amber-500/40">
                      SIMULATED
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {investigationTimeline.length > 0 && (
        <Panel title="Investigation timeline">
          <ul className="text-sm space-y-2 max-h-96 overflow-y-auto">
            {investigationTimeline.map((entry, i) => (
              <li key={`${entry.type}-${entry.ref_id ?? i}`} className="flex gap-3 items-start">
                <span className="text-xs tabular-nums text-muted shrink-0 w-36">
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/40 text-muted border border-border-subtle">
                      {TIMELINE_TYPE_LABELS[entry.type] ?? entry.type}
                    </span>
                    {entry.severity && <SeverityBadge severity={entry.severity} />}
                    <TimelineEntryLink entry={entry} hostId={host?.id}>{entry.title}</TimelineEntryLink>
                    {entry.simulated && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-200 border border-amber-500/40">
                        SIMULATED
                      </span>
                    )}
                  </div>
                  {entry.type === "event" && entry.description && (
                    <details className="mt-1">
                      <summary className="text-xs text-muted cursor-pointer">Raw event</summary>
                      <pre className="mt-1 text-[11px] font-mono text-muted whitespace-pre-wrap break-all max-h-32 overflow-y-auto">
                        {entry.description}
                      </pre>
                    </details>
                  )}
                  {entry.type !== "event" && entry.description && (
                    <p className="text-xs text-muted mt-0.5 truncate">{entry.description}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      {events.length > 0 && investigationTimeline.length === 0 && (
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

function TimelineEntryLink({
  entry,
  hostId,
  children,
}: {
  entry: WorkspaceTimelineEntry;
  hostId?: string;
  children: React.ReactNode;
}) {
  let href: string | null = null;
  if (entry.type === "alert" && entry.ref_id) href = workspaceHref({ alertId: entry.ref_id });
  else if (entry.type === "offense" && entry.ref_id) href = workspaceHref({ offenseId: entry.ref_id });
  else if (entry.type === "incident" && entry.ref_id) href = `/incidents/${entry.ref_id}`;
  else if (entry.type === "event" && hostId) {
    const params = new URLSearchParams({ host_id: hostId, include_simulated: "true" });
    href = `/events?${params.toString()}`;
  }

  if (!href) return <span className="min-w-0 truncate">{children}</span>;
  return (
    <Link href={href} className="hover:text-accent min-w-0 truncate">
      {children}
    </Link>
  );
}

function IncidentNoteForm({
  onSubmit,
  pending,
  disabled,
}: {
  onSubmit: (content: string) => void;
  pending?: boolean;
  disabled?: boolean;
}) {
  const [content, setContent] = useState("");

  if (disabled) return null;

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
