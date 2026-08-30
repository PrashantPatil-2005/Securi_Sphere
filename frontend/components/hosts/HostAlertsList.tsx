"use client";

import { memo } from "react";
import Link from "next/link";
import { AlertTriangle, ExternalLink } from "lucide-react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";

interface HostAlert {
  id: string;
  title: string;
  severity: string;
  status: string;
  created_at: string;
}

interface HostAlertsListProps {
  alerts: HostAlert[];
  hostId: string;
  total?: number;
  isLoading: boolean;
}

function HostAlertsListInner({ alerts, hostId, total = 0, isLoading }: HostAlertsListProps) {
  return (
    <Card>
      <CardHeader
        title="Alerts"
        subtitle={`${total.toLocaleString()} alerts`}
        action={
          <Link
            href={`/alerts?host_id=${hostId}`}
            className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
          >
            View all
            <ExternalLink className="w-3 h-3" />
          </Link>
        }
      />
      <div className="divide-y divide-border-subtle">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-3 w-12 skeleton rounded" />
                <div className="h-3 flex-1 skeleton rounded" />
              </div>
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-4 text-sm text-muted flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-muted" />
            No alerts for this host.
          </div>
        ) : (
          alerts.map((alert) => (
            <Link
              key={alert.id}
              href={`/alerts/${alert.id}`}
              className="flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <SeverityBadge severity={alert.severity} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">{alert.title}</p>
                <p className="text-[10px] text-muted capitalize">{alert.status}</p>
              </div>
              <span className="text-[10px] text-muted tabular-nums shrink-0">
                {new Date(alert.created_at).toLocaleDateString()}
              </span>
            </Link>
          ))
        )}
      </div>
    </Card>
  );
}

export const HostAlertsList = memo(HostAlertsListInner);
