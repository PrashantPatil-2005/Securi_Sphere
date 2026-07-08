"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader, Panel, StatCard } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { cn } from "@/lib/utils/cn";
import { api } from "@/lib/api";
import { BackupPanel } from "@/components/BackupPanel";
import { SystemOpsConsole } from "@/components/admin/SystemOpsConsole";

interface Health {
  status: string;
  checks: Record<string, string>;
  environment: string;
  search_backend?: string;
  opensearch?: {
    status?: string;
    cluster_name?: string;
    number_of_nodes?: number;
    indices?: number;
    events_indices?: number;
    events_docs?: number;
    alerts_docs?: number;
    hosts_docs?: number;
    oldest_event_index?: string | null;
    ism_retention_days?: number;
  } | null;
  job_queue_running: boolean;
  job_queue_backend?: string;
  job_queue_pending?: number;
  ws_pubsub_backend?: string;
  redis_configured: boolean;
  simulation_enabled: boolean;
  registration_enabled: boolean;
}

interface PipelineLayer {
  layer: number;
  name: string;
  qradar_equivalent: string;
  status: string;
  components: { id: string; name: string; endpoint?: string; path?: string; backend?: string }[];
  functions: string[];
  stats: Record<string, string | number>;
}

interface Pipeline {
  model: string;
  description: string;
  layers: PipelineLayer[];
  console: { name: string; qradar_equivalent: string; features: string[]; ui_routes: string[] };
}

interface Stats {
  hosts_total: number;
  hosts_online: number;
  alerts_open: number;
  alerts_critical: number;
  retention_days: number;
}

export default function SystemHealthPage() {
  const { data: health, isLoading: h1, isError: healthError, refetch: refetchHealth } = useQuery({
    queryKey: ["system", "health"],
    queryFn: () => api<Health>("/api/v1/system/health"),
    refetchInterval: 30_000,
  });
  const { data: stats, isLoading: h2, isError: statsError, refetch: refetchStats } = useQuery({
    queryKey: ["system", "stats"],
    queryFn: () => api<Stats>("/api/v1/system/stats"),
    refetchInterval: 30_000,
  });
  const { data: pipeline, isLoading: h3, isError: pipelineError, refetch: refetchPipeline } = useQuery({
    queryKey: ["system", "pipeline"],
    queryFn: () => api<Pipeline>("/api/v1/system/pipeline"),
    refetchInterval: 60_000,
  });

  if (h1 || h2 || h3) return <TableSkeleton rows={6} />;

  if (healthError || statsError || pipelineError) {
    return (
      <div className="space-y-6">
        <PageHeader title="System Health" subtitle="Platform readiness and operational metrics (admin)" />
        <QueryError onRetry={() => { refetchHealth(); refetchStats(); refetchPipeline(); }} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="System Health" subtitle="QRadar-style pipeline status and platform metrics (admin)" />
      <SystemOpsConsole />
      <div className="grid md:grid-cols-4 gap-4">
        <StatCard label="Hosts online" value={`${stats?.hosts_online ?? 0}/${stats?.hosts_total ?? 0}`} tone="success" href="/hosts" />
        <StatCard label="Open alerts" value={stats?.alerts_open} tone="warning" href="/alerts" />
        <StatCard label="Critical alerts" value={stats?.alerts_critical} tone="danger" href="/alerts" />
        <StatCard label="Retention" value={`${stats?.retention_days ?? 0} days`} />
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        <Panel title="SIEM pipeline" subtitle={pipeline?.model ?? "3-layer model"} className="md:col-span-2">
          <p className="text-caption normal-case text-muted mb-4">{pipeline?.description}</p>
          <div className="grid md:grid-cols-3 gap-4">
            {pipeline?.layers.map((layer) => (
              <div key={layer.layer} className="glass-panel p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-caption normal-case font-semibold uppercase tracking-wide text-muted">Layer {layer.layer}</span>
                  <span className={cn("text-caption normal-case capitalize", layer.status === "ok" ? "text-success" : "text-warning")}>
                    {layer.status}
                  </span>
                </div>
                <p className="text-body font-medium mb-1">{layer.name}</p>
                <p className="text-caption normal-case text-muted mb-3">≈ {layer.qradar_equivalent}</p>
                <ul className="text-caption normal-case space-y-1 text-muted">
                  {layer.components.map((c) => (
                    <li key={c.id}>• {c.name}{c.endpoint ? ` (${c.endpoint})` : ""}</li>
                  ))}
                </ul>
                {Object.keys(layer.stats).length > 0 && (
                  <p className="text-caption normal-case text-muted mt-3 pt-3 border-t border-border-subtle/50">
                    {Object.entries(layer.stats).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                  </p>
                )}
              </div>
            ))}
          </div>
          {pipeline?.console && (
            <div className="mt-4 p-4 rounded-lg border border-border-subtle bg-[var(--input-bg)]">
              <p className="text-body font-medium text-foreground">{pipeline.console.name}</p>
              <p className="text-caption normal-case text-muted mt-1">{pipeline.console.features.join(", ")}</p>
            </div>
          )}
        </Panel>
        <Panel title="Readiness" subtitle={`Environment: ${health?.environment ?? "—"}`}>
          <p className="text-body capitalize mb-3">
            Status:{" "}
            <span className={health?.status === "ready" ? "text-success font-medium" : "text-warning font-medium"}>
              {health?.status}
            </span>
          </p>
          <ul className="space-y-2">
            {health && Object.entries(health.checks).map(([k, v]) => (
              <li key={k} className="flex items-center justify-between gap-4 py-2 border-b border-border-subtle/50 last:border-0 text-body">
                <span className="text-muted capitalize">{k.replace(/_/g, " ")}</span>
                <span className="capitalize">{v}</span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Configuration" subtitle="Runtime services and feature flags">
          <ul className="space-y-2">
            <li className="flex items-center justify-between gap-4 py-2 border-b border-border-subtle/50 text-body">
              <span className="text-muted">Job queue</span>
              <span>
                {health?.job_queue_running ? "running" : "stopped"}
                {health?.job_queue_backend ? ` (${health.job_queue_backend})` : ""}
                {health?.job_queue_pending != null ? ` · ${health.job_queue_pending} pending` : ""}
              </span>
            </li>
            <li className="flex items-center justify-between gap-4 py-2 border-b border-border-subtle/50 text-body">
              <span className="text-muted">WebSocket pub/sub</span>
              <span>{health?.ws_pubsub_backend ?? "memory"}</span>
            </li>
            <li className="flex items-center justify-between gap-4 py-2 border-b border-border-subtle/50 text-body">
              <span className="text-muted">Search backend</span>
              <span className="capitalize">{health?.search_backend ?? "postgres"}</span>
            </li>
            <li className="flex items-center justify-between gap-4 py-2 border-b border-border-subtle/50 text-body">
              <span className="text-muted">OpenSearch</span>
              <span className="text-right text-sm">
                {health?.opensearch ? (
                  <>
                    {health.opensearch.status ?? "unknown"}
                    {health.opensearch.number_of_nodes != null ? ` · ${health.opensearch.number_of_nodes} nodes` : ""}
                    {health.opensearch.indices != null ? ` · ${health.opensearch.indices} indices` : ""}
                    {health.opensearch.events_docs != null ? ` · ${health.opensearch.events_docs.toLocaleString()} event docs` : ""}
                    {health.opensearch.ism_retention_days != null ? ` · ISM ${health.opensearch.ism_retention_days}d` : ""}
                    {health.opensearch.oldest_event_index ? (
                      <span className="block text-xs text-muted mt-0.5">oldest: {health.opensearch.oldest_event_index}</span>
                    ) : null}
                  </>
                ) : (
                  "not configured (Postgres search)"
                )}
              </span>
            </li>
            <li className="flex items-center justify-between gap-4 py-2 border-b border-border-subtle/50 text-body">
              <span className="text-muted">Redis</span>
              <span>{health?.redis_configured ? "configured" : "not configured"}</span>
            </li>
            <li className="flex items-center justify-between gap-4 py-2 border-b border-border-subtle/50 text-body">
              <span className="text-muted">Registration</span>
              <span>{health?.registration_enabled ? "open" : "closed"}</span>
            </li>
            <li className="flex items-center justify-between gap-4 py-2 text-body">
              <span className="text-muted">Simulation</span>
              <span>{health?.simulation_enabled ? "enabled" : "disabled"}</span>
            </li>
          </ul>
        </Panel>
        <BackupPanel />
      </div>
    </div>
  );
}
