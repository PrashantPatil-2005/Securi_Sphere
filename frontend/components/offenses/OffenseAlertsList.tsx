"use client";

import Link from "next/link";
import { SeverityBadge } from "@/components/design-system/Badge";
import type { OffenseAlertRef } from "@/lib/types/offense";

interface Props {
  alerts: OffenseAlertRef[];
}

export function OffenseAlertsList({ alerts }: Props) {
  if (!alerts.length) {
    return (
      <div className="p-4 rounded-xl border border-border-subtle bg-surface">
        <p className="text-xs text-muted">No related alerts.</p>
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <h3 className="text-sm font-semibold mb-3">Related Alerts ({alerts.length})</h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {alerts.map((a) => (
          <Link
            key={a.id}
            href={`/alerts/${a.id}`}
            className="flex items-center gap-2 p-2 rounded-lg hover:bg-surface-hover transition-colors group"
          >
            <SeverityBadge severity={a.severity} />
            <span className="flex-1 text-sm truncate group-hover:text-accent transition-colors">
              {a.title}
            </span>
            <span className="text-[10px] text-muted shrink-0 capitalize">{a.status}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
