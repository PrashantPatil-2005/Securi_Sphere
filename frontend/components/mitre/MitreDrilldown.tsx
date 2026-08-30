"use client";

import { memo } from "react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";
import { EmptyState } from "@/components/design-system/EmptyState";
import type { MitreDrilldownResponse } from "@/lib/types/mitre";
import Link from "next/link";

interface MitreDrilldownProps {
  data: MitreDrilldownResponse | undefined;
  isLoading: boolean;
  onClose: () => void;
}

function MitreDrilldownInner({ data, isLoading }: MitreDrilldownProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader title="Technique" subtitle="Loading..." />
        <div className="p-4 space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-4 skeleton rounded w-3/4" />
          ))}
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <EmptyState
          title="Select a technique"
          description="Click a technique in the matrix to see detailed information."
        />
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title={`${data.technique_id} — ${data.name}`}
        subtitle={data.tactic}
      />
      <div className="p-4 space-y-5">
        {data.description && (
          <p className="text-sm text-muted leading-relaxed">{data.description}</p>
        )}

        {/* Counts */}
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-3 rounded-lg bg-card-elevated border border-border-subtle">
            <p className="text-2xl font-semibold tabular-nums text-accent">{data.event_count}</p>
            <p className="text-xs text-muted mt-1">Events</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-card-elevated border border-border-subtle">
            <p className="text-2xl font-semibold tabular-nums text-warning">{data.alert_count}</p>
            <p className="text-xs text-muted mt-1">Alerts</p>
          </div>
        </div>

        {/* Links */}
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/events?mitre_technique_id=${encodeURIComponent(data.technique_id)}`}
            className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline"
          >
            View all events →
          </Link>
          <Link
            href={`/alerts?mitre_technique_id=${encodeURIComponent(data.technique_id)}`}
            className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline"
          >
            View all alerts →
          </Link>
        </div>

        {/* Top hosts */}
        {data.top_hosts.length > 0 && (
          <section>
            <h3 className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Top hosts</h3>
            <div className="space-y-1">
              {data.top_hosts.map((h) => (
                <div key={h.host_id} className="flex justify-between text-sm px-3 py-2 rounded bg-card-elevated border border-border-subtle">
                  <Link href={`/hosts/${h.host_id}`} className="hover:text-accent truncate">
                    {h.host_name}
                  </Link>
                  <span className="text-muted tabular-nums shrink-0 ml-2">{h.event_count}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent alerts */}
        {data.recent_alerts.length > 0 && (
          <section>
            <h3 className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Recent alerts</h3>
            <div className="space-y-2">
              {data.recent_alerts.map((a) => (
                <Link
                  key={a.id}
                  href={`/alerts/${a.id}`}
                  className="block px-3 py-2 rounded bg-card-elevated border border-border-subtle hover:border-accent/30 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <SeverityBadge severity={a.severity} />
                    <span className="text-[10px] text-muted tabular-nums">
                      {new Date(a.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-xs font-medium truncate">{a.title}</p>
                  <p className="text-[10px] text-muted capitalize">{a.status}</p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Recent events */}
        {data.recent_events.length > 0 && (
          <section>
            <h3 className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Recent events</h3>
            <div className="space-y-2">
              {data.recent_events.map((e) => (
                <div key={e.id} className="px-3 py-2 rounded bg-card-elevated border border-border-subtle">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <SeverityBadge severity={e.severity} />
                    <span className="text-[10px] text-muted tabular-nums">
                      {new Date(e.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-accent">{e.event_type}</p>
                  {e.description && (
                    <p className="text-[11px] text-muted mt-0.5 line-clamp-2">{e.description}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {data.event_count === 0 && data.alert_count === 0 && (
          <p className="text-sm text-muted">No matching events or alerts in the selected time range.</p>
        )}
      </div>
    </Card>
  );
}

export const MitreDrilldown = memo(MitreDrilldownInner);
