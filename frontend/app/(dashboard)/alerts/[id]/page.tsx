"use client";

import { useCallback, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Target,
  Brain,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  Shield,
  Clock,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import { cn } from "@/lib/utils/cn";
import {
  useAlertInvestigation,
  useAlertAiSummary,
  useAlertStatusMutation,
  useAlertFeedbackMutation,
} from "@/lib/hooks/useAlerts";
import { useAssistant } from "@/lib/assistant/AssistantProvider";
import { useToast } from "@/components/ui/Toast";
import { SeverityBadge, StatusBadge } from "@/components/design-system/Badge";
import { Card, CardHeader } from "@/components/design-system/Card";
import { Button } from "@/components/design-system/Button";
import { LoadingState, ErrorState } from "@/components/design-system";
import { EventDetailDrawer } from "@/components/alerts/EventDetailDrawer";
import type { AlertEvent, AlertHost } from "@/lib/types/alert";
import type { AlertRule } from "@/lib/hooks/useRules";

interface RelatedOffense {
  id: string;
  offense_number: number;
  title: string;
  status: string;
  host_id: string;
}

function useRelatedOffenses(alertId: string | null) {
  return useQuery({
    queryKey: ["offenses", "related", alertId],
    queryFn: async () => {
      const res = await api<{ items: RelatedOffense[] }>(
        `${API.OFFENSES.LIST}?page=1&page_size=100`,
      );
      return (res.items ?? []).filter(
        (o) =>
          o.host_id === alertId ||
          o.id === alertId,
      );
    },
    enabled: !!alertId,
    staleTime: 60_000,
  });
}

function useAlertRule(ruleId: string | null) {
  return useQuery({
    queryKey: ["alert-rules", ruleId],
    queryFn: () => api<AlertRule>(API.ALERT_RULES.DETAIL(ruleId!)),
    enabled: !!ruleId,
    staleTime: 60_000,
  });
}

function ConfidenceBar({ value }: { value: number | null }) {
  if (value === null || value === undefined) {
    return <span className="text-xs text-muted">No confidence data</span>;
  }
  const pct = Math.round(value * 100);
  const color =
    pct >= 80
      ? "bg-severity-critical"
      : pct >= 60
        ? "bg-severity-high"
        : pct >= 40
          ? "bg-severity-medium"
          : "bg-severity-low";
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className="text-xs text-muted">Confidence</span>
        <span className="text-sm font-semibold tabular-nums">{pct}%</span>
      </div>
      <div className="h-1.5 bg-card-elevated rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/alerts"
      className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-foreground transition-colors mb-4"
    >
      <ArrowLeft className="w-3.5 h-3.5" />
      Back to Alerts
    </Link>
  );
}

function PageLoadingSkeleton() {
  return (
    <div className="space-y-4">
      <BackLink />
      <div className="skeleton h-20 w-full rounded-lg" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="skeleton h-40 rounded-lg" />
        <div className="skeleton h-40 rounded-lg" />
      </div>
      <div className="skeleton h-32 rounded-lg" />
      <div className="skeleton h-48 rounded-lg" />
    </div>
  );
}

function AlertHeader({
  alert,
}: {
  alert: { title: string; severity: string; status: string; confidence: number | null; description: string | null; created_at: string };
}) {
  return (
    <Card>
      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={alert.severity} />
            <StatusBadge status={alert.status} />
          </div>
          <h1 className="text-lg font-semibold text-foreground leading-tight">{alert.title}</h1>
          {alert.description && (
            <p className="text-sm text-muted leading-relaxed">{alert.description}</p>
          )}
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(alert.created_at).toLocaleString()}
            </span>
            <ConfidenceBar value={alert.confidence} />
          </div>
        </div>
      </div>
    </Card>
  );
}

function InfoGrid({ host }: { host: AlertHost | null }) {
  return (
    <Card>
      <CardHeader title="Host Information" subtitle="Target asset details" />
      {host ? (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
          <dt className="text-muted">Name</dt>
          <dd className="font-medium text-foreground">{host.name}</dd>
          {host.hostname && (
            <>
              <dt className="text-muted">Hostname</dt>
              <dd className="font-mono text-xs text-foreground">{host.hostname}</dd>
            </>
          )}
          {host.ip_address && (
            <>
              <dt className="text-muted">IP Address</dt>
              <dd className="font-mono text-xs text-foreground">{host.ip_address}</dd>
            </>
          )}
          <dt className="text-muted">Status</dt>
          <dd>
            <StatusBadge status={host.status} />
          </dd>
          {host.risk_score !== null && (
            <>
              <dt className="text-muted">Risk Score</dt>
              <dd className="font-semibold tabular-nums">{host.risk_score}</dd>
            </>
          )}
        </dl>
      ) : (
        <p className="text-sm text-muted">No host data available</p>
      )}
    </Card>
  );
}

function AnalystActions({
  alert,
  isUpdating,
  onStatusChange,
  onAskAi,
  hasFeedback,
}: {
  alert: { id: string; status: string; feedback_label: string | null };
  isUpdating: boolean;
  onStatusChange: (status: string) => void;
  onAskAi: () => void;
  hasFeedback: boolean;
}) {
  const statuses = ["open", "investigating", "resolved", "closed"] as const;

  return (
    <Card>
      <CardHeader title="Analyst Actions" subtitle="Status and triage controls" />
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {statuses.map((s) => (
            <Button
              key={s}
              type="button"
              variant={alert.status === s ? "primary" : "ghost"}
              size="sm"
              loading={isUpdating}
              onClick={() => onStatusChange(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </Button>
          ))}
        </div>

        <div className="border-t border-border-subtle pt-3 space-y-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon={<Brain className="w-4 h-4" />}
            onClick={onAskAi}
          >
            Ask AI Assistant
          </Button>

          {hasFeedback && (
            <div className="flex items-center gap-2 text-xs text-success">
              <ThumbsUp className="w-3 h-3" />
              Feedback submitted
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function DetectionExplanation({
  alert,
  rule,
}: {
  alert: { confidence: number | null; rule_id: string | null };
  rule: AlertRule | undefined;
}) {
  return (
    <Card>
      <CardHeader title="Detection Explanation" subtitle="How this alert was triggered" />
      <div className="space-y-3">
        {rule ? (
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <dt className="text-xs text-muted">Rule Name</dt>
              <dd className="font-medium text-foreground mt-0.5">{rule.name}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Rule Type</dt>
              <dd className="font-mono text-xs mt-0.5">{rule.rule_type}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Threshold</dt>
              <dd className="tabular-nums mt-0.5">
                {rule.threshold ?? "—"} events / {rule.window_minutes ?? "—"} min
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Severity</dt>
              <dd className="mt-0.5"><SeverityBadge severity={rule.severity} /></dd>
            </div>
          </dl>
        ) : alert.rule_id ? (
          <p className="text-sm text-muted">
            Rule <code className="font-mono text-xs">{alert.rule_id}</code> (details unavailable)
          </p>
        ) : (
          <p className="text-sm text-muted">No associated rule</p>
        )}

        <div className="border-t border-border-subtle pt-3">
          <ConfidenceBar value={alert.confidence} />
        </div>
      </div>
    </Card>
  );
}

function AttackStory({ timelines }: { timelines: Array<{ id: string; title: string; severity: string; confidence: number; started_at: string; status: string }> }) {
  if (timelines.length === 0) {
    return (
      <Card>
        <CardHeader title="Attack Story" subtitle="Correlated event timelines" />
        <p className="text-sm text-muted">No correlated timelines found</p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Attack Story" subtitle="Correlated event timelines" />
      <div className="space-y-2">
        {timelines.map((t) => (
          <div
            key={t.id}
            className="flex items-start gap-3 p-3 rounded-lg border border-border-subtle bg-card-elevated/50 hover:bg-card-elevated transition-colors"
          >
            <div
              className={cn(
                "w-2 h-2 rounded-full mt-1.5 shrink-0",
                t.severity === "critical"
                  ? "bg-severity-critical"
                  : t.severity === "high"
                    ? "bg-severity-high"
                    : t.severity === "medium"
                      ? "bg-severity-medium"
                      : "bg-severity-low",
              )}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground truncate">{t.title}</span>
                <StatusBadge status={t.status} />
              </div>
              <div className="flex items-center gap-3 mt-1 text-xs text-muted">
                <span>{new Date(t.started_at).toLocaleString()}</span>
                <span className="tabular-nums">{Math.round(t.confidence * 100)}% confidence</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function RelatedEvents({
  events,
  onEventClick,
}: {
  events: AlertEvent[];
  onEventClick: (event: AlertEvent) => void;
}) {
  if (events.length === 0) {
    return (
      <Card>
        <CardHeader title="Related Events" subtitle="Events in the ±30 minute window" />
        <p className="text-sm text-muted">No related events found</p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Related Events"
        subtitle={`${events.length} events in the ±30 minute window`}
      />
      <div className="space-y-1.5 max-h-80 overflow-y-auto">
        {events.map((event) => (
          <button
            key={event.id}
            type="button"
            onClick={() => onEventClick(event)}
            className="w-full text-left p-2.5 rounded-lg border border-border-subtle hover:border-border hover:bg-card-elevated transition-colors group"
          >
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono font-medium text-foreground truncate">
                {event.event_type}
              </code>
              <SeverityBadge severity={event.severity} />
              <ExternalLink className="w-3 h-3 text-muted opacity-0 group-hover:opacity-100 transition-opacity ml-auto shrink-0" />
            </div>
            {event.description && (
              <p className="text-xs text-muted mt-1 truncate">{event.description}</p>
            )}
            <time className="text-[10px] text-muted tabular-nums mt-1 block">
              {new Date(event.timestamp).toLocaleString()}
            </time>
          </button>
        ))}
      </div>
    </Card>
  );
}

function MitreSection({
  techniqueId,
  tactic,
}: {
  techniqueId: string | null;
  tactic: string | null;
}) {
  if (!techniqueId && !tactic) {
    return (
      <Card>
        <CardHeader title="MITRE ATT&CK" subtitle="Technique classification" />
        <p className="text-sm text-muted">No MITRE mapping available</p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="MITRE ATT&CK" subtitle="Technique classification" />
      <dl className="space-y-3 text-sm">
        {tactic && (
          <div>
            <dt className="text-xs text-muted">Tactic</dt>
            <dd className="font-medium text-foreground mt-0.5 flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5 text-severity-high" />
              {tactic}
            </dd>
          </div>
        )}
        {techniqueId && (
          <div>
            <dt className="text-xs text-muted">Technique ID</dt>
            <dd className="font-mono text-xs mt-0.5">
              <a
                href={`https://attack.mitre.org/techniques/${techniqueId}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent hover:underline inline-flex items-center gap-1"
              >
                {techniqueId}
                <ExternalLink className="w-3 h-3" />
              </a>
            </dd>
          </div>
        )}
      </dl>
    </Card>
  );
}

function RelatedOffenseSection({
  offenses,
  loading,
}: {
  offenses: RelatedOffense[];
  loading: boolean;
}) {
  if (loading) {
    return (
      <Card>
        <CardHeader title="Related Offense" subtitle="Linked offense records" />
        <LoadingState variant="inline" text="Loading offenses…" />
      </Card>
    );
  }

  if (offenses.length === 0) {
    return (
      <Card>
        <CardHeader title="Related Offense" subtitle="Linked offense records" />
        <p className="text-sm text-muted">No related offenses found</p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Related Offense" subtitle={`${offenses.length} linked offense(s)`} />
      <div className="space-y-2">
        {offenses.map((o) => (
          <Link
            key={o.id}
            href={`/offenses/${o.id}`}
            className="flex items-center gap-3 p-2.5 rounded-lg border border-border-subtle hover:border-border hover:bg-card-elevated transition-colors group"
          >
            <Shield className="w-4 h-4 text-severity-high shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground truncate">Offense #{o.offense_number}</span>
                <StatusBadge status={o.status} />
              </div>
              <p className="text-xs text-muted truncate mt-0.5">{o.title}</p>
            </div>
            <ExternalLink className="w-3 h-3 text-muted opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
          </Link>
        ))}
      </div>
    </Card>
  );
}

function AiSummarySection({
  aiSummary,
  isLoading,
  isError,
}: {
  aiSummary: { summary: string; investigation_steps: string[]; recommended_actions: string[] } | undefined;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader title="AI Analysis" subtitle="Machine-generated investigation brief" />
        <LoadingState variant="inline" text="Generating analysis…" />
      </Card>
    );
  }

  if (isError || !aiSummary) return null;

  return (
    <Card>
      <CardHeader
        title="AI Analysis"
        subtitle="Machine-generated investigation brief"
        action={
          <span className="text-xs text-muted inline-flex items-center gap-1">
            <Brain className="w-3 h-3" />
            AI Generated
          </span>
        }
      />
      <div className="space-y-3">
        <p className="text-sm text-foreground leading-relaxed">{aiSummary.summary}</p>

        {aiSummary.investigation_steps.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted uppercase tracking-wide mb-1.5">
              Investigation Steps
            </h4>
            <ol className="list-decimal list-inside space-y-1 text-sm text-foreground">
              {aiSummary.investigation_steps.map((step, i) => (
                <li key={i} className="leading-relaxed">{step}</li>
              ))}
            </ol>
          </div>
        )}

        {aiSummary.recommended_actions.length > 0 && (
          <div>
            <h4 className="text-xs font-medium text-muted uppercase tracking-wide mb-1.5">
              Recommended Actions
            </h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-foreground">
              {aiSummary.recommended_actions.map((action, i) => (
                <li key={i} className="leading-relaxed">{action}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  );
}

function FeedbackSection({
  alertId,
  currentLabel,
  currentNote,
}: {
  alertId: string;
  currentLabel: string | null;
  currentNote: string | null;
}) {
  const [note, setNote] = useState("");
  const feedbackMutation = useAlertFeedbackMutation(alertId);
  const { toast } = useToast();

  const submitFeedback = useCallback(
    (label: "false_positive" | "true_positive") => {
      feedbackMutation.mutate(
        { label, note: note || undefined },
        {
          onSuccess: () => {
            setNote("");
            toast("success", "Feedback submitted");
          },
          onError: (e: Error) =>
            toast("error", "Feedback submission failed", e.message),
        },
      );
    },
    [feedbackMutation, note, toast],
  );

  return (
    <Card>
      <CardHeader title="Feedback" subtitle="Improve detection accuracy" />
      {currentLabel ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            {currentLabel === "true_positive" ? (
              <ThumbsUp className="w-4 h-4 text-success" />
            ) : (
              <ThumbsDown className="w-4 h-4 text-danger" />
            )}
            <span className="font-medium">
              {currentLabel === "true_positive" ? "True Positive" : "False Positive"}
            </span>
          </div>
          {currentNote && (
            <p className="text-xs text-muted">{currentNote}</p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Optional note…"
            className="w-full text-sm rounded-lg border border-border-subtle bg-card-elevated px-3 py-2 text-foreground placeholder:text-muted resize-none focus:outline-none focus:ring-1 focus:ring-accent/50"
            rows={2}
          />
          <div className="flex gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              icon={<ThumbsUp className="w-3.5 h-3.5" />}
              loading={feedbackMutation.isPending}
              onClick={() => submitFeedback("true_positive")}
            >
              True Positive
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              icon={<ThumbsDown className="w-3.5 h-3.5" />}
              loading={feedbackMutation.isPending}
              onClick={() => submitFeedback("false_positive")}
            >
              False Positive
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function AlertDetailPage() {
  const params = useParams<{ id: string }>();
  const alertId = params?.id ?? null;
  const { openWithContext } = useAssistant();
  const { toast } = useToast();

  const [selectedEvent, setSelectedEvent] = useState<AlertEvent | null>(null);

  const {
    data: investigation,
    isLoading,
    isError,
    error,
    refetch,
  } = useAlertInvestigation(alertId);

  const {
    data: aiSummary,
    isLoading: aiLoading,
    isError: aiError,
  } = useAlertAiSummary(alertId);

  const alertRule = useAlertRule(investigation?.alert.rule_id ?? null);

  const {
    data: relatedOffenses = [],
    isLoading: offensesLoading,
  } = useRelatedOffenses(alertId);

  const statusMutation = useAlertStatusMutation();

  const handleStatusChange = useCallback(
    (status: string) => {
      if (!alertId) return;
      statusMutation.mutate(
        { id: alertId, status },
        {
          onSuccess: () => toast("success", `Status updated to ${status}`),
          onError: (e: Error) =>
            toast("error", "Status update failed", e.message),
        },
      );
    },
    [alertId, statusMutation, toast],
  );

  const handleEventClick = useCallback((event: AlertEvent) => {
    setSelectedEvent(event);
  }, []);

  const handleAskAi = useCallback(() => {
    if (!alertId) return;
    openWithContext({ alertId });
  }, [alertId, openWithContext]);

  const hasFeedback = !!investigation?.alert.feedback_label;

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <PageLoadingSkeleton />
      </div>
    );
  }

  if (isError || !investigation) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <BackLink />
        <ErrorState
          variant="page"
          title="Failed to load alert"
          description={error instanceof Error ? error.message : "An unexpected error occurred"}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const { alert, host, events, timelines } = investigation;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
      <BackLink />

      <AlertHeader alert={alert} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <InfoGrid host={host} />
        <AnalystActions
          alert={alert}
          isUpdating={statusMutation.isPending}
          onStatusChange={handleStatusChange}
          onAskAi={handleAskAi}
          hasFeedback={hasFeedback}
        />
      </div>

      <DetectionExplanation alert={alert} rule={alertRule.data} />

      <AiSummarySection
        aiSummary={aiSummary}
        isLoading={aiLoading}
        isError={aiError}
      />

      <AttackStory timelines={timelines} />

      <RelatedEvents events={events} onEventClick={handleEventClick} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MitreSection
          techniqueId={alert.mitre_technique_id}
          tactic={alert.mitre_tactic}
        />
        <RelatedOffenseSection
          offenses={relatedOffenses}
          loading={offensesLoading}
        />
      </div>

      <FeedbackSection
        alertId={alert.id}
        currentLabel={alert.feedback_label}
        currentNote={alert.feedback_note}
      />

      <EventDetailDrawer
        event={selectedEvent}
        open={!!selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />
    </div>
  );
}
