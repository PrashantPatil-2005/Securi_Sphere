"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { SeverityBadge, StatusBadge } from "@/components/design-system/Badge";
import type { IncidentDetail } from "@/lib/types/incident";

interface Props {
  incident: IncidentDetail;
}

export function IncidentDetailHeader({ incident }: Props) {
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
            </div>
            <h1 className="text-lg font-semibold">{incident.title}</h1>
            {incident.description && (
              <p className="text-sm text-muted mt-1">{incident.description}</p>
            )}
          </div>

          <Link
            href={`/investigation?incidentId=${incident.id}`}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-border-subtle hover:bg-surface-hover transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Case Workspace
          </Link>
        </div>

        <div className="flex items-center gap-4 mt-3 text-xs text-muted">
          <span>Created {new Date(incident.created_at).toLocaleString()}</span>
          {incident.resolved_at && (
            <>
              <span>·</span>
              <span>Resolved {new Date(incident.resolved_at).toLocaleString()}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
