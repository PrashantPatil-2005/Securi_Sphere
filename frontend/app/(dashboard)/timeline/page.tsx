"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { PageHeader } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { EmptyState } from "@/components/ui/Panel";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils/cn";

interface Timeline {
  id: string;
  host_id: string;
  title: string;
  description: string | null;
  started_at: string;
  ended_at: string;
  mitre_techniques: string[];
  severity: string;
  confidence: number;
  status: string;
}

interface TEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  mitre_technique_id: string | null;
  timestamp: string;
}

export default function TimelinePage() {
  const { queryParams } = useTimeRange();
  const [selected, setSelected] = useState<string | null>(null);
  const { data: items = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["timelines", queryParams],
    queryFn: () => api<Timeline[]>(`/api/v1/timelines${buildQuery({ page_size: 100 }, queryParams)}`),
  });

  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ["timeline-events", selected],
    queryFn: () => api<TEvent[]>(`/api/v1/timelines/${selected}/events`),
    enabled: !!selected,
  });

  const active = items.find((t) => t.id === selected);

  return (
    <div className="space-y-6">
      <PageHeader title="Attack Timelines" subtitle="Reconstructed attack chains with MITRE technique mapping" />
      <TimeRangeBar />
      {isLoading && <TableSkeleton rows={4} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {!isLoading && !isError && items.length === 0 && (
        <EmptyState title="No attack timelines" description="Run a simulation or wait for correlated activity to build chains." />
      )}
      <div className="grid lg:grid-cols-[minmax(280px,1fr)_minmax(360px,1.2fr)] gap-6">
        <div className="space-y-3">
          {items.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setSelected(t.id)}
              className={cn(
                "w-full text-left glass-panel p-4 transition-colors",
                selected === t.id && "border-accent/50 ring-1 ring-accent/30",
              )}
            >
              <div className="flex justify-between items-start gap-2">
                <span className="font-medium">{t.title}</span>
                <SeverityBadge severity={t.severity} />
              </div>
              <p className="text-sm text-muted mt-1 line-clamp-2">{t.description}</p>
              <div className="text-xs text-muted mt-2 tabular-nums">
                {new Date(t.started_at).toLocaleString()} — {new Date(t.ended_at).toLocaleString()}
                <span className="ml-2 text-accent">{t.confidence.toFixed(0)}% confidence</span>
              </div>
              {t.mitre_techniques?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {t.mitre_techniques.map((m) => (
                    <span key={m} className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                      {m}
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
        <GlassPanel className="min-h-[420px]">
          {!selected && <p className="text-muted text-sm">Select a timeline to view the attack chain.</p>}
          {selected && active && (
            <div>
              <div className="mb-6 pb-4 border-b border-border-subtle">
                <h2 className="text-heading font-semibold">{active.title}</h2>
                <p className="text-sm text-muted mt-1">{active.description}</p>
              </div>
              {eventsLoading && <TableSkeleton rows={4} />}
              <div className="relative pl-6 space-y-0">
                {events.map((e, i) => (
                  <div key={e.id} className="relative pb-6 last:pb-0">
                    {i < events.length - 1 && (
                      <div className="absolute left-[5px] top-3 bottom-0 w-px bg-border-subtle" />
                    )}
                    <div className="absolute left-0 top-1.5 w-2.5 h-2.5 rounded-full bg-accent ring-4 ring-accent/20" />
                    <div className="ml-4">
                      <p className="text-xs text-muted tabular-nums">{new Date(e.timestamp).toLocaleString()}</p>
                      <p className="font-medium mt-0.5">{e.event_type}</p>
                      {e.description && <p className="text-sm text-muted mt-0.5">{e.description}</p>}
                      <div className="flex items-center gap-2 mt-1">
                        <SeverityBadge severity={e.severity} />
                        {e.mitre_technique_id && (
                          <span className="text-[10px] font-mono text-accent">{e.mitre_technique_id}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </GlassPanel>
      </div>
    </div>
  );
}
