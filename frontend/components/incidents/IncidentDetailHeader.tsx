"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { StatusBadge, SeverityBadge, Badge } from "@/components/design-system/Badge";
import type { IncidentDetail, IncidentStatus } from "@/lib/types/incident";
import { INCIDENT_STATUS_TRANSITIONS } from "@/lib/types/incident";
import { Button } from "@/components/ui/Button";

interface IncidentDetailHeaderProps {
  incident: IncidentDetail;
  onStatusChange?: (status: string) => void;
  isUpdating?: boolean;
}

const STATUS_ACTIONS: Record<string, string> = {
  open: "Reopen",
  investigating: "Investigate",
  resolved: "Resolve",
  closed: "Close",
};

export function IncidentDetailHeader({
  incident,
  onStatusChange,
  isUpdating,
}: IncidentDetailHeaderProps) {
  const transitions = INCIDENT_STATUS_TRANSITIONS[incident.status as IncidentStatus] ?? [];

  return (
    <div className="space-y-3">
      <Link
        href="/incidents"
        className="inline-flex items-center gap-1 text-xs text-muted hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-3 h-3" />
        Back to Incidents
      </Link>

      <div className="p-4 rounded-xl border border-border-subtle bg-surface">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
              {incident.simulated && (
                <Badge variant="default" className="badge-info">
                  {incident.source || "Synthetic"}
                </Badge>
              )}
            </div>
            <h1 className="text-lg font-semibold">{incident.title}</h1>
            {incident.description && (
              <p className="text-sm text-muted mt-1">{incident.description}</p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-muted">
          <span>Created {new Date(incident.created_at).toLocaleString()}</span>
          {incident.resolved_at && (
            <>
              <span>·</span>
              <span>Resolved {new Date(incident.resolved_at).toLocaleString()}</span>
            </>
          )}
          {incident.host_id && (
            <span>
              ·<span className="font-mono text-[11px] ml-1">{incident.host_id}</span>
            </span>
          )}
          {incident.alert_ids.length > 0 && (
            <span>· {incident.alert_ids.length} linked alert(s)</span>
          )}
        </div>

        {onStatusChange && (
          <div className="mt-4 pt-4 border-t border-border-subtle">
            <p className="text-xs text-muted mb-2">Status</p>
            <div className="flex flex-wrap gap-1">
              {transitions.map((s) => (
                <Button
                  key={s}
                  variant={s === "resolved" ? "primary" : "ghost"}
                  size="sm"
                  disabled={isUpdating}
                  onClick={() => onStatusChange(s)}
                >
                  {STATUS_ACTIONS[s] ?? s}
                </Button>
              ))}
              {transitions.length === 0 && (
                <span className="text-xs text-muted">No further transitions.</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
