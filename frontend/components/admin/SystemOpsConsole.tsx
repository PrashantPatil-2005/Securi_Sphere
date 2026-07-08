"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { RefreshCw, Database, Activity, Server } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, StatCard } from "@/components/ui/Panel";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { Button } from "@/components/ui/Button";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/Toast";
import { useUxEnabled } from "@/lib/featureFlags";
import { track } from "@/lib/telemetry";
import { useState } from "react";

interface CircuitSnapshot {
  name: string;
  state: string;
  failure_count?: number;
}

interface MvView {
  name: string;
  ispopulated?: boolean;
  last_refresh?: string | null;
}

export function SystemOpsConsole() {
  const enabled = useUxEnabled("ux_admin_ops_console_enabled");
  const { toast } = useToast();
  const [mvConfirm, setMvConfirm] = useState(false);
  const [backfillConfirm, setBackfillConfirm] = useState(false);

  const { data: circuits, isLoading: c1, isError: e1, refetch: r1 } = useQuery({
    queryKey: ["system", "circuits"],
    queryFn: () => api<{ enabled: boolean; circuits: CircuitSnapshot[] }>("/api/v1/system/circuits"),
    enabled,
    refetchInterval: 30_000,
  });

  const { data: pool, isLoading: c2, refetch: r2 } = useQuery({
    queryKey: ["system", "pool"],
    queryFn: () => api<Record<string, unknown>>("/api/v1/system/pool"),
    enabled,
    refetchInterval: 60_000,
  });

  const { data: replicas, refetch: r3 } = useQuery({
    queryKey: ["system", "replicas"],
    queryFn: () => api<{ lag_seconds?: number; status?: string; read_url_configured?: boolean }>("/api/v1/system/replicas"),
    enabled,
    refetchInterval: 30_000,
  });

  const { data: mvs, refetch: r4 } = useQuery({
    queryKey: ["system", "analytics-mvs"],
    queryFn: () => api<{ enabled: boolean; views: MvView[] }>("/api/v1/system/analytics-mvs"),
    enabled,
    refetchInterval: 60_000,
  });

  const { data: telemetry } = useQuery({
    queryKey: ["telemetry", "summary"],
    queryFn: () => api<{ funnel: Record<string, number>; total: number }>("/api/v1/telemetry/summary?days=7"),
    enabled,
    staleTime: 120_000,
  });

  const mvRefresh = useMutation({
    mutationFn: () => api("/api/v1/system/analytics-mvs/refresh", { method: "POST" }),
    onSuccess: () => {
      toast("success", "Analytics views refreshed");
      track("admin_ops_action", { action: "mv_refresh" });
      r4();
    },
    onError: (e: Error) => toast("error", "Refresh failed", e.message),
  });

  const backfill = useMutation({
    mutationFn: () => api("/api/v1/system/opensearch/backfill", { method: "POST" }),
    onSuccess: () => {
      toast("success", "OpenSearch backfill started");
      track("admin_ops_action", { action: "opensearch_backfill" });
    },
    onError: (e: Error) => toast("error", "Backfill failed", e.message),
  });

  if (!enabled) return null;
  if (c1 || c2) return <TableSkeleton rows={4} />;
  if (e1) return <QueryError onRetry={() => { r1(); r2(); r3(); r4(); }} />;

  const openCircuits = (circuits?.circuits ?? []).filter((c) => c.state !== "closed");
  const replicaLag = replicas?.lag_seconds ?? 0;
  const degraded = openCircuits.length > 0 || replicaLag > 30;

  return (
    <div className="space-y-4">
      {degraded && (
        <EmotionBanner
          tone="urgency"
          title="Platform needs attention"
          message={
            openCircuits.length
              ? `${openCircuits.length} circuit breaker(s) open — check downstream services.`
              : `Read replica lag is ${replicaLag}s — dashboards may show stale data.`
          }
          action={
            <Button type="button" variant="ghost" size="sm" onClick={() => { r1(); r3(); }}>
              <RefreshCw className="w-3.5 h-3.5" />
              Recheck
            </Button>
          }
        />
      )}

      <div className="grid md:grid-cols-4 gap-3">
        <StatCard label="Open circuits" value={openCircuits.length} tone={openCircuits.length ? "danger" : "success"} />
        <StatCard label="Replica lag" value={`${replicaLag}s`} tone={replicaLag > 30 ? "warning" : "success"} />
        <StatCard label="MV views" value={mvs?.views?.length ?? 0} tone="info" />
        <StatCard label="UX events (7d)" value={telemetry?.total ?? 0} tone="info" />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Panel title="Circuit breakers" subtitle="Outbound dependency health">
          <ul className="space-y-2 text-sm">
            {(circuits?.circuits ?? []).slice(0, 8).map((c) => (
              <li key={c.name} className="flex justify-between gap-2 py-1 border-b border-border-subtle/50 last:border-0">
                <span className="text-muted">{c.name}</span>
                <span className={c.state === "closed" ? "text-success capitalize" : "text-warning capitalize"}>{c.state}</span>
              </li>
            ))}
            {!circuits?.circuits?.length && <p className="text-muted text-sm">No circuits registered.</p>}
          </ul>
        </Panel>

        <Panel title="Database pool" subtitle="Connection utilization">
          <div className="flex items-center gap-2 text-sm text-muted mb-2">
            <Database className="w-4 h-4" />
            Primary + read replica pools
          </div>
          <pre className="text-xs bg-[var(--input-bg)] p-3 rounded border border-border-subtle overflow-auto max-h-40">
            {JSON.stringify(pool ?? {}, null, 2)}
          </pre>
        </Panel>

        <Panel title="Analytics materialized views" subtitle="Dashboard freshness">
          <ul className="space-y-1 text-sm mb-3">
            {(mvs?.views ?? []).map((v) => (
              <li key={v.name} className="flex justify-between gap-2">
                <span>{v.name}</span>
                <span className={v.ispopulated ? "text-success" : "text-warning"}>
                  {v.ispopulated ? "ready" : "stale"}
                </span>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <Button type="button" size="sm" loading={mvRefresh.isPending} onClick={() => setMvConfirm(true)}>
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh MVs
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setBackfillConfirm(true)}>
              <Server className="w-3.5 h-3.5" />
              OpenSearch backfill
            </Button>
          </div>
        </Panel>

        <Panel title="Conversion funnel (7d)" subtitle="Product telemetry">
          <div className="flex items-center gap-2 text-sm text-muted mb-2">
            <Activity className="w-4 h-4" />
            Activation metrics from client events
          </div>
          <ul className="space-y-1 text-sm">
            {Object.entries(telemetry?.funnel ?? {}).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2 py-1">
                <span className="text-muted">{k.replace(/_/g, " ")}</span>
                <span className="tabular-nums font-medium">{v}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <ConfirmDialog
        open={mvConfirm}
        onClose={() => setMvConfirm(false)}
        onConfirm={() => { mvRefresh.mutate(); setMvConfirm(false); }}
        title="Refresh analytics views"
        description="Rebuild materialized views used by SIEM dashboards. May take a few seconds."
        confirmLabel="Refresh"
        loading={mvRefresh.isPending}
      />
      <ConfirmDialog
        open={backfillConfirm}
        onClose={() => setBackfillConfirm(false)}
        onConfirm={() => { backfill.mutate(); setBackfillConfirm(false); }}
        title="OpenSearch backfill"
        description="Bulk reindex events and alerts. Use during maintenance windows only."
        confirmLabel="Start backfill"
        danger
        loading={backfill.isPending}
      />
    </div>
  );
}
