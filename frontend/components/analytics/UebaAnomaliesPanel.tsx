"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { FlaskConical } from "lucide-react";
import { api } from "@/lib/api";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";

interface UebaSummary {
  open_count: number;
  by_severity: Record<string, number>;
  enabled: boolean;
  z_threshold: number;
  baseline_days: number;
}

interface UebaAnomaly {
  id: string;
  entity_type: string;
  entity_key: string;
  entity_label: string;
  metric: string;
  observed_value: number;
  baseline_mean: number;
  z_score: number;
  severity: string;
  status: string;
  description: string;
  alert_id: string | null;
  detected_at: string;
}

export function UebaAnomaliesPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: summary } = useQuery({
    queryKey: ["ueba", "summary"],
    queryFn: () => api<UebaSummary>("/api/v1/ueba/summary"),
    staleTime: 60_000,
  });

  const { data: anomalies = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["ueba", "anomalies"],
    queryFn: () => api<UebaAnomaly[]>("/api/v1/ueba/anomalies?status=open&limit=25"),
    staleTime: 30_000,
  });

  const scanMutation = useMutation({
    mutationFn: () => api<{ created: number; updated: number }>("/api/v1/ueba/scan", { method: "POST" }),
    onSuccess: (res) => {
      toast("success", "UEBA scan complete", `${res.created} new, ${res.updated} updated`);
      queryClient.invalidateQueries({ queryKey: ["ueba"] });
    },
    onError: (e: Error) => toast("error", "Scan failed", e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: "dismissed" | "resolved" }) =>
      api(`/api/v1/ueba/anomalies/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ueba"] }),
    onError: (e: Error) => toast("error", "Update failed", e.message),
  });

  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <Panel
      title="UEBA baseline anomalies"
      subtitle={
        summary
          ? `Z-score ≥ ${summary.z_threshold} vs ${summary.baseline_days}-day baseline · ${summary.open_count} open`
          : "Behavioral spikes vs rolling baselines"
      }
      action={
        <Button size="sm" variant="ghost" loading={scanMutation.isPending} onClick={() => scanMutation.mutate()}>
          Run scan
        </Button>
      }
    >
      {isLoading ? (
        <TableSkeleton rows={4} />
      ) : anomalies.length === 0 ? (
        <EmptyState
          title="No open anomalies"
          description="Run an Attack Lab simulation to generate behavioral baselines, then scan for z-score spikes."
          icon={<FlaskConical className="w-8 h-8" />}
          action="/simulation"
          actionLabel="Open Attack Lab"
        />
      ) : (
        <div className="space-y-2">
          {anomalies.map((a) => (
            <div key={a.id} className="p-3 glass-panel">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium flex items-center gap-2 flex-wrap">
                    <span>{a.entity_label}</span>
                    <span className="text-xs text-muted capitalize">{a.entity_type}</span>
                    <SeverityBadge severity={a.severity} />
                  </p>
                  <p className="text-xs text-muted mt-0.5">
                    {a.metric.replace(/_/g, " ")} · observed {a.observed_value} · z={a.z_score.toFixed(1)} · μ={a.baseline_mean.toFixed(1)}
                  </p>
                  <p className="text-sm mt-1">{a.description}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  {a.alert_id && (
                    <Link href={workspaceHref({ alertId: a.alert_id })} className="btn-ghost text-xs">
                      Case Workspace
                    </Link>
                  )}
                  {a.entity_type === "host" && (
                    <Link href={`/hosts?selected=${a.entity_key}`} className="btn-ghost text-xs">
                      Host
                    </Link>
                  )}
                  <button type="button" className="btn-ghost text-xs" onClick={() => updateMutation.mutate({ id: a.id, status: "dismissed" })}>
                    Dismiss
                  </button>
                  <button type="button" className={cn("btn-ghost text-xs")} onClick={() => updateMutation.mutate({ id: a.id, status: "resolved" })}>
                    Resolve
                  </button>
                </div>
              </div>
              <p className="text-[10px] text-muted mt-2">{new Date(a.detected_at).toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
