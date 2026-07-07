"use client";

import Link from "next/link";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/Panel";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";

interface OffenseDetailData {
  id: string;
  offense_number: number;
  host_name: string;
  title: string;
  risk_level: string;
  status: string;
  incident_id?: string | null;
  events: { event_type: string; description: string | null; timestamp: string; severity: string }[];
  alerts: { id: string; title: string; severity: string; status: string; created_at: string }[];
  timeline?: { ts: string; type: string; detail: string }[];
  related_hosts?: string[];
  related_users?: string[];
}

interface AiBrief {
  brief: string;
  key_findings: string[];
  recommended_actions: string[];
}

const riskClass = (r: string) =>
  r === "critical" ? "text-red-400" : r === "high" ? "text-orange-400" : r === "medium" ? "text-yellow-400" : "text-gray-400";

export function OffenseDetailPanel({
  selectedId,
  selected,
  detailLoading,
  aiBrief,
  promotePending,
  onPromote,
  onViewInvestigation,
  onStatus,
}: {
  selectedId: string | null;
  selected?: OffenseDetailData;
  detailLoading: boolean;
  aiBrief?: AiBrief;
  promotePending: boolean;
  onPromote: (id: string) => void;
  onViewInvestigation: (incidentId: string) => void;
  onStatus: (id: string, status: string) => void;
}) {
  if (detailLoading) return <TableSkeleton rows={4} />;
  if (!selectedId) {
    return <EmptyState title="Select an offense" description="Choose an offense from the list to view details." />;
  }
  if (!selected) return null;

  return (
    <>
      <h2 className="font-semibold text-lg">{selected.title}</h2>
      <p className="text-sm text-muted mb-4">
        Host: {selected.host_name} · Risk: <span className={riskClass(selected.risk_level)}>{selected.risk_level}</span>
      </p>
      {aiBrief && (
        <div className="mb-4 p-3 rounded-lg border border-border-subtle bg-[var(--input-bg)]">
          <p className="text-caption normal-case text-muted mb-1">AI threat brief</p>
          <p className="text-sm text-muted mb-2">{aiBrief.brief}</p>
          {aiBrief.key_findings.length > 0 && (
            <ul className="text-xs text-muted list-disc list-inside space-y-0.5">
              {aiBrief.key_findings.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {(selected.related_hosts?.length || selected.related_users?.length) ? (
        <div className="mb-4 p-3 glass-panel">
          <p className="text-caption normal-case text-muted mb-2">Related entities</p>
          <div className="flex flex-wrap gap-2">
            {selected.related_hosts?.map((h) => (
              <span key={h} className="text-xs px-2 py-1 rounded bg-accent/10 text-accent font-mono">
                host:{h.slice(0, 8)}
              </span>
            ))}
            {selected.related_users?.map((u) => (
              <span key={u} className="text-xs px-2 py-1 rounded bg-warning/10 text-warning">
                user:{u}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2 mb-4">
        <Link href={workspaceHref({ offenseId: selected.id })} className="btn-ghost text-xs">
          Open Case Workspace
        </Link>
        <button
          type="button"
          className="btn-primary text-xs"
          disabled={promotePending}
          onClick={() => {
            if (selected.incident_id) {
              onViewInvestigation(selected.incident_id);
            } else {
              onPromote(selected.id);
            }
          }}
        >
          {selected.incident_id ? "View in Case Workspace" : "Promote to incident"}
        </button>
        {(["open", "investigating", "resolved"] as const).map((s) => (
          <button
            key={s}
            type="button"
            className="btn-ghost text-xs capitalize"
            onClick={() => onStatus(selected.id, s)}
          >
            {s}
          </button>
        ))}
      </div>
      <div className="space-y-2 text-sm max-h-64 overflow-y-auto">
        {(selected.timeline ?? []).length > 0 && (
          <div className="mb-3">
            <p className="text-caption normal-case text-muted mb-1">Timeline</p>
            {(selected.timeline ?? []).map((t, i) => (
              <div key={i} className="p-2 rounded bg-accent/5 text-xs font-mono">
                {t.ts}: {t.detail || t.type}
              </div>
            ))}
          </div>
        )}
        {selected.alerts.map((a) => (
          <div key={a.id} className="p-2 rounded bg-[var(--input-bg)]">
            [{a.severity}] {a.title}
          </div>
        ))}
        {selected.events.map((e, i) => (
          <div key={i} className="p-2 rounded bg-[var(--input-bg)] font-mono text-xs">
            {e.event_type}: {e.description}
          </div>
        ))}
      </div>
    </>
  );
}