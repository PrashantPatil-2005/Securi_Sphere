"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { Sheet } from "@/components/ui/Sheet";
import { QueryError } from "@/components/ui/QueryError";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { GlassPanel } from "@/components/ui/GlassPanel";

interface DrilldownData {
  technique_id: string;
  tactic: string;
  name: string;
  description: string | null;
  event_count: number;
  alert_count: number;
  top_hosts: { host_id: string; host_name: string; event_count: number }[];
  recent_events: {
    id: string;
    host_id: string;
    event_type: string;
    severity: string;
    description: string | null;
    timestamp: string;
  }[];
  recent_alerts: {
    id: string;
    host_id: string;
    title: string;
    severity: string;
    status: string;
    created_at: string;
  }[];
}

interface MitreTechniqueDrilldownProps {
  techniqueId: string | null;
  queryParams: Record<string, string>;
  onClose: () => void;
}

export function MitreTechniqueDrilldown({ techniqueId, queryParams, onClose }: MitreTechniqueDrilldownProps) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["mitre-drilldown", techniqueId, queryParams],
    queryFn: () =>
      api<DrilldownData>(
        `/api/v1/mitre/techniques/${encodeURIComponent(techniqueId!)}/drilldown${buildQuery({}, queryParams)}`,
      ),
    enabled: !!techniqueId,
  });

  const eventsHref = techniqueId
    ? `/events${buildQuery({ mitre_technique_id: techniqueId }, queryParams)}`
    : "/events";
  const alertsHref = techniqueId
    ? `/alerts${buildQuery({ mitre_technique_id: techniqueId }, queryParams)}`
    : "/alerts";

  return (
    <Sheet
      open={!!techniqueId}
      onClose={onClose}
      title={data ? `${data.technique_id} · ${data.name}` : techniqueId ?? "Technique"}
      description={data?.tactic}
      className="max-w-xl"
    >
      {isLoading && <TableSkeleton rows={5} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {data && (
        <div className="space-y-5 pb-6">
          {data.description && (
            <p className="text-sm text-muted leading-relaxed">{data.description}</p>
          )}

          <div className="grid grid-cols-2 gap-3">
            <GlassPanel className="text-center py-3">
              <p className="text-2xl font-semibold tabular-nums text-accent">{data.event_count}</p>
              <p className="text-caption text-muted">Events</p>
            </GlassPanel>
            <GlassPanel className="text-center py-3">
              <p className="text-2xl font-semibold tabular-nums text-accent">{data.alert_count}</p>
              <p className="text-caption text-muted">Alerts</p>
            </GlassPanel>
          </div>

          <div className="flex flex-wrap gap-2">
            <Link
              href={eventsHref}
              className="inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
            >
              View all events <ExternalLink className="w-3.5 h-3.5" />
            </Link>
            <Link
              href={alertsHref}
              className="inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
            >
              View all alerts <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>

          {data.top_hosts.length > 0 && (
            <section>
              <h3 className="text-subheading mb-2">Top hosts</h3>
              <ul className="space-y-1.5">
                {data.top_hosts.map((h) => (
                  <li key={h.host_id} className="flex justify-between gap-2 text-sm glass-panel px-3 py-2 rounded">
                    <Link
                      href={`/events${buildQuery({ host_id: h.host_id, mitre_technique_id: techniqueId! }, queryParams)}`}
                      className="truncate hover:text-accent"
                    >
                      {h.host_name}
                    </Link>
                    <span className="text-muted tabular-nums shrink-0">{h.event_count}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.recent_alerts.length > 0 && (
            <section>
              <h3 className="text-subheading mb-2">Recent alerts</h3>
              <ul className="space-y-2">
                {data.recent_alerts.map((a) => (
                  <li key={a.id} className="glass-panel px-3 py-2 rounded text-sm">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <SeverityBadge severity={a.severity} />
                      <span className="text-[11px] text-muted tabular-nums">
                        {new Date(a.created_at).toLocaleString()}
                      </span>
                    </div>
                    <Link
                      href={workspaceHref({ alertId: a.id })}
                      className="font-medium hover:text-accent line-clamp-2"
                    >
                      {a.title}
                    </Link>
                    <p className="text-xs text-muted mt-0.5 capitalize">{a.status}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.recent_events.length > 0 && (
            <section>
              <h3 className="text-subheading mb-2">Recent events</h3>
              <ul className="space-y-2">
                {data.recent_events.map((e) => (
                  <li key={e.id} className="glass-panel px-3 py-2 rounded text-sm">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <SeverityBadge severity={e.severity} />
                      <span className="text-[11px] text-muted tabular-nums">
                        {new Date(e.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="font-mono text-xs text-accent">{e.event_type}</p>
                    {e.description && <p className="text-muted line-clamp-2 mt-0.5">{e.description}</p>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.event_count === 0 && data.alert_count === 0 && (
            <p className="text-sm text-muted">No matching events or alerts in the selected time range.</p>
          )}
        </div>
      )}
    </Sheet>
  );
}
