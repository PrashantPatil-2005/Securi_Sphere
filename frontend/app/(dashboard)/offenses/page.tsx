"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import TimeRangeBar from "@/components/TimeRangeBar";
import { InvestigationTrail } from "@/components/InvestigationTrail";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { useToast } from "@/components/ui/Toast";

interface Offense {
  id: string;
  offense_number: number;
  host_id?: string;
  host_name: string;
  title: string;
  risk_level: string;
  status: string;
  event_count: number;
  created_at: string;
}

interface OffenseDetail extends Offense {
  incident_id?: string | null;
  events: { event_type: string; description: string | null; timestamp: string; severity: string }[];
  alerts: { id: string; title: string; severity: string; status: string; created_at: string }[];
  timeline?: { ts: string; type: string; detail: string }[];
  related_hosts?: string[];
  related_users?: string[];
}

export default function OffensesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { queryParams } = useTimeRange();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("selected"));

  useEffect(() => {
    const id = searchParams.get("selected");
    if (id) setSelectedId(id);
  }, [searchParams]);

  const { data, isLoading } = useQuery({
    queryKey: ["offenses", queryParams],
    queryFn: () => api<{ items: Offense[] }>(`/api/v1/offenses${buildQuery({}, queryParams)}`),
  });

  const { data: selected, isLoading: detailLoading } = useQuery({
    queryKey: ["offenses", selectedId],
    queryFn: () => api<OffenseDetail>(`/api/v1/offenses/${selectedId}`),
    enabled: !!selectedId,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/offenses/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
      toast("success", "Offense updated");
    },
    onError: (e: Error) => toast("error", "Update failed", e.message),
  });

  const promoteMutation = useMutation({
    mutationFn: (id: string) =>
      api<{ incident_id: string; created: boolean; linked_alert_count: number }>(
        `/api/v1/offenses/${id}/promote-to-incident`,
        { method: "POST" },
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      toast("success", data.created ? "Investigation opened" : "Opening existing investigation");
      router.push(`/incidents?selected=${data.incident_id}`);
    },
    onError: (e: Error) => toast("error", "Promotion failed", e.message),
  });

  const offenses = data?.items ?? [];
  const riskClass = (r: string) =>
    r === "critical" ? "text-red-400" : r === "high" ? "text-orange-400" : r === "medium" ? "text-yellow-400" : "text-gray-400";

  return (
    <div className="space-y-6">
      <PageHeader title="Offense Management" subtitle="Correlated security offenses grouped from related alerts and events" />
      <InvestigationTrail
        offenseId={selectedId ?? undefined}
        hostId={selected?.host_id}
        hostName={selected?.host_name}
        incidentId={selected?.incident_id ?? undefined}
      />
      <TimeRangeBar />
      {isLoading && <TableSkeleton rows={6} />}
      <div className="grid lg:grid-cols-2 gap-6">
        <Panel title="Offenses">
          <div className="space-y-2 max-h-[32rem] overflow-y-auto">
            {offenses.map((o) => (
              <button
                key={o.id}
                type="button"
                onClick={() => setSelectedId(o.id)}
                className={`w-full text-left p-3 rounded border transition-colors ${selectedId === o.id ? "border-accent bg-accent/10" : "border-border-subtle hover:bg-[var(--sidebar-hover)]"}`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-mono text-accent">#{o.offense_number}</span>
                  <span className={`text-xs uppercase ${riskClass(o.risk_level)}`}>{o.risk_level}</span>
                </div>
                <p className="font-medium mt-1">{o.title}</p>
                <p className="text-xs text-muted mt-1">{o.host_name} · {o.event_count} events · {o.status}</p>
              </button>
            ))}
            {!isLoading && offenses.length === 0 && <EmptyState title="No offenses" description="No offenses in selected range." />}
          </div>
        </Panel>
        <Panel title="Details">
          {detailLoading && <TableSkeleton rows={4} />}
          {selected && !detailLoading && (
            <>
              <h2 className="font-semibold text-lg">{selected.title}</h2>
              <p className="text-sm text-muted mb-4">Host: {selected.host_name} · Risk: {selected.risk_level}</p>
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  type="button"
                  className="btn-primary text-xs"
                  disabled={promoteMutation.isPending}
                  onClick={() => {
                    if (selected.incident_id) {
                      router.push(`/incidents?selected=${selected.incident_id}`);
                    } else {
                      promoteMutation.mutate(selected.id);
                    }
                  }}
                >
                  {selected.incident_id ? "View investigation" : "Open investigation"}
                </button>
                {(["open", "investigating", "resolved"] as const).map((s) => (
                  <button key={s} type="button" className="btn-ghost text-xs capitalize" onClick={() => statusMutation.mutate({ id: selected.id, status: s })}>
                    {s}
                  </button>
                ))}
              </div>
              <div className="space-y-2 text-sm max-h-64 overflow-y-auto">
                {(selected.timeline ?? []).length > 0 && (
                  <div className="mb-3">
                    <p className="text-caption normal-case text-muted mb-1">Timeline</p>
                    {(selected.timeline ?? []).map((t, i) => (
                      <div key={i} className="p-2 rounded bg-accent/5 text-xs font-mono">{t.ts}: {t.detail || t.type}</div>
                    ))}
                  </div>
                )}
                {selected.alerts.map((a) => (
                  <div key={a.id} className="p-2 rounded bg-[var(--input-bg)]">[{a.severity}] {a.title}</div>
                ))}
                {selected.events.map((e, i) => (
                  <div key={i} className="p-2 rounded bg-[var(--input-bg)] font-mono text-xs">{e.event_type}: {e.description}</div>
                ))}
              </div>
            </>
          )}
          {!selectedId && !detailLoading && <EmptyState title="Select an offense" description="Choose an offense from the list to view details." />}
        </Panel>
      </div>
    </div>
  );
}
