"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { SeverityBadge } from "@/components/design-system/Badge";

interface AlertRef {
  id: string;
  title?: string;
  severity?: string;
  status?: string;
}

interface Props {
  alertIds: string[];
  alerts?: AlertRef[];
}

export function IncidentAlertsList({ alertIds, alerts }: Props) {
  if (!alertIds.length) {
    return (
      <div className="p-4 rounded-xl border border-border-subtle bg-surface">
        <p className="text-xs text-muted">No linked alerts.</p>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <h3 className="text-sm font-semibold mb-3">Linked Alerts ({alertIds.length})</h3>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {alertIds.map((id) => {
          const alert = alerts?.find((a) => a.id === id);
          return (
            <Link
              key={id}
              href={`/alerts/${id}`}
              className="flex items-center gap-2 p-2 rounded-lg hover:bg-surface-hover transition-colors group"
            >
              {alert?.severity && <SeverityBadge severity={alert.severity} />}
              <span className="flex-1 text-sm truncate group-hover:text-accent transition-colors">
                {alert?.title ?? id.slice(0, 8) + "…"}
              </span>
              <ExternalLink className="w-3 h-3 text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          );
        })}
      </div>
    </div>
  );
}
