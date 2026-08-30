"use client";

import { memo } from "react";
import { SeverityBadge, StatusBadge } from "@/components/design-system/Badge";
import { cn } from "@/lib/utils/cn";
import type { IncidentSummary } from "@/lib/types/incident";

interface Props {
  incident: IncidentSummary;
  selected: boolean;
  onClick: () => void;
}

export const IncidentRow = memo(function IncidentRow({ incident, selected, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full text-left p-3 rounded-lg border transition-colors",
        selected
          ? "border-accent bg-accent/10"
          : "border-border-subtle hover:bg-surface-hover",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <SeverityBadge severity={incident.severity} />
            <StatusBadge status={incident.status} />
          </div>
          <p className="font-medium text-sm truncate">{incident.title}</p>
          {incident.description && (
            <p className="text-xs text-muted mt-1 line-clamp-2">{incident.description}</p>
          )}
          <div className="flex items-center gap-2 mt-1 text-xs text-muted">
            <span>{new Date(incident.created_at).toLocaleDateString()}</span>
            {incident.resolved_at && (
              <>
                <span>·</span>
                <span>Resolved {new Date(incident.resolved_at).toLocaleDateString()}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </button>
  );
});
