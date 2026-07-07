"use client";

import { Suspense } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import { useDeepLinkedSelection, workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import TimeRangeBar from "@/components/TimeRangeBar";
import { InvestigationTrail } from "@/components/InvestigationTrail";
import { OffenseDetailPanel } from "@/components/offenses/OffenseDetailPanel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { Drawer } from "@/components/ui/Drawer";
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
  return (
    <Suspense fallback={<TableSkeleton rows={6} />}>
      <OffensesPageContent />
    </Suspense>
  );
}

function OffensesPageContent() {
  const router = useRouter();
  const { queryParams } = useTimeRange();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [selectedId, setSelectedId] = useDeepLinkedSelection();
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["offenses", queryParams],
    queryFn: () => api<{ items: Offense[] }>(`/api/v1/offenses${buildQuery({}, queryParams)}`),
  });

  const { data: selected, isLoading: detailLoading } = useQuery({
    queryKey: ["offenses", selectedId],
    queryFn: () => api<OffenseDetail>(`/api/v1/offenses/${selectedId}`),
    enabled: !!selectedId,
  });

  const { data: aiBrief } = useQuery({
    queryKey: ["offenses", "ai-brief", selectedId],
    queryFn: () =>
      api<{
        brief: string;
        key_findings: string[];
        recommended_actions: string[];
      }>(`/api/v1/offenses/${selectedId}/ai-brief`),
    enabled: !!selectedId,
    staleTime: 120_000,
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
      queryClient.invalidateQueries({ queryKey: ["incidents", "count"] });
      toast("success", data.created ? "Incident opened in Case Workspace" : "Opening existing incident");
      router.push(workspaceHref({ incidentId: data.incident_id }));
    },
    onError: (e: Error) => toast("error", "Promotion failed", e.message),
  });

  const offenses = data?.items ?? [];
  const riskClass = (r: string) =>
    r === "critical" ? "text-red-400" : r === "high" ? "text-orange-400" : r === "medium" ? "text-yellow-400" : "text-gray-400";

  const detailPanel = (
    <OffenseDetailPanel
      selectedId={selectedId}
      selected={selected}
      detailLoading={detailLoading}
      aiBrief={aiBrief}
      promotePending={promoteMutation.isPending}
      onPromote={(id) => promoteMutation.mutate(id)}
      onViewInvestigation={(incidentId) => router.push(workspaceHref({ incidentId }))}
      onStatus={(id, status) => statusMutation.mutate({ id, status })}
    />
  );

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
      {isError && <QueryError onRetry={() => refetch()} />}
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
            {!isLoading && offenses.length === 0 && (
              <EmptyState
                title="No offenses"
                description="Offenses appear when correlation rules group related alerts. Try running a simulation."
                icon={<ShieldAlert className="w-10 h-10 opacity-40" />}
                action="/simulation"
                actionLabel="Run simulation"
              />
            )}
          </div>
        </Panel>
        <Panel title="Details" className="hidden lg:block">
          {detailPanel}
        </Panel>
      </div>

      <Drawer
        open={!!selectedId && !isDesktop}
        onClose={() => setSelectedId(null)}
        title="Offense details"
        side="bottom"
        className="lg:hidden"
      >
        {detailPanel}
      </Drawer>
    </div>
  );
}
