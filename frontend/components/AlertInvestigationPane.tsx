"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAssistant } from "@/lib/assistant/AssistantProvider";
import { InvestigationTrail } from "@/components/InvestigationTrail";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { IocLookupPanel } from "@/components/IocLookupPanel";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { TriageStepper } from "@/components/alerts/TriageStepper";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { useUxEnabled } from "@/lib/featureFlags";
import { track } from "@/lib/telemetry";

interface InvestigationData {
  alert: {
    id: string;
    host_id: string;
    title: string;
    description: string | null;
    severity: string;
    status: string;
    confidence: number | null;
    mitre_technique_id: string | null;
    created_at: string;
    feedback_label: string | null;
    feedback_note: string | null;
  };
  host: {
    id: string;
    name: string;
    hostname: string | null;
    status: string;
    ip_address: string | null;
    risk_score: number | null;
  };
  events: {
    id: string;
    event_type: string;
    severity: string;
    description: string | null;
    timestamp: string;
  }[];
  timelines: {
    id: string;
    title: string;
    severity: string;
    confidence: number;
    started_at: string;
    status: string;
  }[];
}

export function AlertInvestigationPane({
  alertId,
  onStatus,
  isUpdating,
}: {
  alertId: string | null;
  onStatus: (id: string, status: string) => void;
  isUpdating?: boolean;
}) {
  const { openWithContext } = useAssistant();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const guidedTriage = useUxEnabled("ux_guided_triage_enabled");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["alerts", "investigation", alertId],
    queryFn: () => api<InvestigationData>(`/api/v1/alerts/${alertId}/investigation`),
    enabled: !!alertId,
  });

  const { data: aiSummary } = useQuery({
    queryKey: ["alerts", "ai-summary", alertId],
    queryFn: () =>
      api<{
        summary: string;
        investigation_steps: string[];
        recommended_actions: string[];
      }>(`/api/v1/alerts/${alertId}/ai-summary`),
    enabled: !!alertId,
    staleTime: 120_000,
  });

  const feedbackMutation = useMutation({
    mutationFn: (payload: { label: "false_positive" | "true_positive"; note?: string }) =>
      api(`/api/v1/alerts/${alertId}/feedback`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alerts", "investigation", alertId] });
      toast("success", vars.label === "false_positive" ? "Marked false positive" : "Marked true positive");
    },
    onError: (e: Error) => toast("error", "Feedback update failed", e.message),
  });

  if (!alertId) {
    return (
      <Panel title="Investigation">
        <EmptyState title="Select an alert" description="Choose an alert from the list to review host context, related events, and timelines." />
      </Panel>
    );
  }

  if (isLoading) return <Panel title="Investigation"><TableSkeleton rows={6} /></Panel>;
  if (isError) return <Panel title="Investigation"><QueryError onRetry={() => refetch()} /></Panel>;
  if (!data) return null;

  const { alert, host, events, timelines } = data;
  const severityTone = alert.severity === "critical" ? "urgency" : alert.severity === "high" ? "progress" : "calm";

  return (
    <div className="space-y-4">
      {guidedTriage && (
        <>
          <EmotionBanner
            tone={severityTone}
            title={
              alert.status === "resolved"
                ? "Triage complete — nice work"
                : alert.severity === "critical"
                  ? "Critical alert needs your attention"
                  : "Work through triage at your pace"
            }
            message={
              alert.status === "open"
                ? "Start investigation, review host context, then classify and resolve."
                : undefined
            }
          />
          <TriageStepper
            status={alert.status}
            severity={alert.severity}
            hasFeedback={!!alert.feedback_label}
          />
        </>
      )}
      <InvestigationTrail hostId={host.id} hostName={host.name} alertId={alert.id} />
      <Panel title="Alert details">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={alert.severity} />
            <span className="text-body font-semibold">{alert.title}</span>
            <span className="text-caption normal-case text-muted capitalize">{alert.status}</span>
            {alert.confidence != null && (
              <span className="text-caption normal-case text-muted">{alert.confidence.toFixed(0)}% confidence</span>
            )}
          </div>
          {alert.description && <p className="text-body text-muted">{alert.description}</p>}
          <p className="text-caption normal-case text-muted tabular-nums">
            Detected {new Date(alert.created_at).toLocaleString()}
            {alert.mitre_technique_id && <> · MITRE {alert.mitre_technique_id}</>}
          </p>
          <div className="flex flex-wrap gap-2">
            {alert.status === "open" && (
              <>
                <button
                  type="button"
                  disabled={isUpdating}
                  onClick={() => {
                    track("alert_triage_started", { alert_id: alert.id, severity: alert.severity });
                    onStatus(alert.id, "investigating");
                  }}
                  className="btn-ghost text-xs"
                >
                  Start investigation
                </button>
                <button
                  type="button"
                  disabled={isUpdating}
                  onClick={() => {
                    track("alert_triage_resolved", { alert_id: alert.id, severity: alert.severity });
                    onStatus(alert.id, "resolved");
                  }}
                  className="btn-ghost text-xs text-success"
                >
                  Resolve
                </button>
              </>
            )}
            {alert.status === "investigating" && (
              <button
                type="button"
                disabled={isUpdating}
                onClick={() => {
                  track("alert_triage_resolved", { alert_id: alert.id, severity: alert.severity });
                  onStatus(alert.id, "resolved");
                }}
                className="btn-ghost text-xs text-success"
              >
                Resolve
              </button>
            )}
            <Link href={`/events?host_id=${host.id}`} className="btn-ghost text-xs">
              All host events
            </Link>
            <Link href={`/timeline?host=${host.id}`} className="btn-ghost text-xs">
              Full timeline
            </Link>
            <Link href={workspaceHref({ alertId: alert.id })} className="btn-primary text-xs">
              Open Case Workspace
            </Link>
            <button
              type="button"
              className="btn-ghost text-xs text-accent flex items-center gap-1"
              onClick={() =>
                openWithContext({
                  alertId: alert.id,
                  prefill: "Explain this alert and suggest investigation steps",
                })
              }
            >
              <Sparkles className="w-3 h-3" />
              Ask AI about this alert
            </button>
            <button
              type="button"
              disabled={feedbackMutation.isPending}
              onClick={() => feedbackMutation.mutate({ label: "false_positive" })}
              className="btn-ghost text-xs"
            >
              Mark false positive
            </button>
            <button
              type="button"
              disabled={feedbackMutation.isPending}
              onClick={() => feedbackMutation.mutate({ label: "true_positive" })}
              className="btn-ghost text-xs"
            >
              Mark true positive
            </button>
          </div>
          {alert.feedback_label && (
            <p className="text-caption normal-case text-muted">
              Feedback: <span className="font-medium capitalize">{alert.feedback_label.replace("_", " ")}</span>
              {alert.feedback_note ? ` · ${alert.feedback_note}` : ""}
            </p>
          )}
        </div>
      </Panel>

      {aiSummary && (
        <Panel title="AI investigation summary" subtitle="Auto-generated triage brief">
          <p className="text-body text-muted mb-3">{aiSummary.summary.replace(/\*\*/g, "")}</p>
          {aiSummary.investigation_steps.length > 0 && (
            <ol className="list-decimal list-inside space-y-1 text-sm text-muted">
              {aiSummary.investigation_steps.map((step, i) => (
                <li key={i}>{step.replace(/\*\*/g, "")}</li>
              ))}
            </ol>
          )}
        </Panel>
      )}

      <Panel title="Affected host">
        <div className="grid sm:grid-cols-2 gap-3 text-body">
          <div>
            <p className="text-caption normal-case text-muted">Name</p>
            <p className="font-medium">{host.name}</p>
          </div>
          <div>
            <p className="text-caption normal-case text-muted">Status</p>
            <p className="capitalize">{host.status}</p>
          </div>
          <div>
            <p className="text-caption normal-case text-muted">Hostname</p>
            <p>{host.hostname ?? "—"}</p>
          </div>
          <div>
            <p className="text-caption normal-case text-muted">IP</p>
            <p className="font-mono text-sm">{host.ip_address ?? "—"}</p>
          </div>
          {host.risk_score != null && (
            <div>
              <p className="text-caption normal-case text-muted">Threat score</p>
              <p className="tabular-nums font-semibold text-warning">{host.risk_score}</p>
            </div>
          )}
        </div>
      </Panel>

      <IocLookupPanel value={host.ip_address} />

      <Panel title={`Related events (${events.length})`} subtitle="±30 minutes around alert time">
        {events.length === 0 ? (
          <p className="text-body text-muted">No events in this window.</p>
        ) : (
          <div className="space-y-2 max-h-56 overflow-y-auto">
            {events.map((event) => (
              <div key={event.id} className="p-2 rounded-lg border border-border-subtle text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <SeverityBadge severity={event.severity} />
                  <span className="font-mono text-xs">{event.event_type}</span>
                  <span className="text-caption normal-case text-muted ml-auto tabular-nums">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {event.description && <p className="text-muted">{event.description}</p>}
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Attack timelines">
        {timelines.length === 0 ? (
          <p className="text-body text-muted">No correlated timelines for this host yet.</p>
        ) : (
          <div className="space-y-2">
            {timelines.map((tl) => (
              <Link
                key={tl.id}
                href={`/timeline?host=${host.id}`}
                className="block p-3 rounded-lg border border-border-subtle hover:border-border hover:bg-[var(--sidebar-hover)] transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-body font-medium">{tl.title}</span>
                  <SeverityBadge severity={tl.severity} />
                </div>
                <p className="text-caption normal-case text-muted mt-1 capitalize">
                  {tl.status} · {tl.confidence.toFixed(0)}% · {new Date(tl.started_at).toLocaleString()}
                </p>
              </Link>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
