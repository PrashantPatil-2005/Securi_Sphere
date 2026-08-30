"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink, Shield } from "lucide-react";
import { SeverityBadge, StatusBadge } from "@/components/design-system/Badge";
import type { OffenseDetail } from "@/lib/types/offense";

interface Props {
  offense: OffenseDetail;
}

export function OffenseDetailHeader({ offense }: Props) {
  return (
    <div className="space-y-3">
      <Link
        href="/offenses"
        className="inline-flex items-center gap-1 text-xs text-muted hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-3 h-3" />
        Back to Offenses
      </Link>

      <div className="p-4 rounded-xl border border-border-subtle bg-surface">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <SeverityBadge severity={offense.risk_level} />
              <span className="font-mono text-sm text-muted">#{offense.offense_number}</span>
              <StatusBadge status={offense.status} />
            </div>
            <h1 className="text-lg font-semibold">{offense.title}</h1>
            {offense.description && (
              <p className="text-sm text-muted mt-1">{offense.description}</p>
            )}
          </div>

          <div className="flex gap-2">
            <Link
              href={`/investigation?offenseId=${offense.id}`}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-accent text-white hover:bg-accent/90 transition-colors"
            >
              <Shield className="w-3 h-3" />
              Case Workspace
            </Link>
            {offense.incident_id && (
              <Link
                href={`/incidents/${offense.incident_id}`}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-border-subtle hover:bg-surface-hover transition-colors"
              >
                <ExternalLink className="w-3 h-3" />
                View Incident
              </Link>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4 mt-3 text-xs text-muted">
          <span>Host: <span className="text-foreground font-medium">{offense.host_name}</span></span>
          <span>·</span>
          <span>{offense.alert_count} alert{offense.alert_count !== 1 ? "s" : ""}</span>
          <span>·</span>
          <span>{offense.event_count} event{offense.event_count !== 1 ? "s" : ""}</span>
          <span>·</span>
          <span>Created {new Date(offense.created_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
