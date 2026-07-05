"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { api } from "@/lib/api";

interface Health {
  status: string;
  checks: Record<string, string>;
  environment: string;
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
      <div className="grid md:grid-cols-2 gap-6">
        <Panel title="SIEM pipeline (3 layers)" className="md:col-span-2">
          <p className="text-sm text-muted mb-4">{pipeline?.description}</p>
          <div className="grid md:grid-cols-3 gap-4">
            {pipeline?.layers.map((layer) => (
              <div key={layer.layer} className="p-4 rounded-lg border border-border-subtle">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted">Layer {layer.layer}</span>
                  <span className={layer.status === "ok" ? "text-success text-xs" : "text-warning text-xs"}>{layer.status}</span>
                </div>
                <p className="font-medium text-sm mb-1">{layer.name}</p>
                <p className="text-xs text-muted mb-3">≈ {layer.qradar_equivalent}</p>
                <ul className="text-xs space-y-1 text-muted">
                  {layer.components.map((c) => (
                    <li key={c.id}>• {c.name}{c.endpoint ? ` (${c.endpoint})` : ""}</li>
                  ))}
                </ul>
                <p className="text-xs text-muted mt-3">
                  {Object.entries(layer.stats).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                </p>
              </div>
            ))}
          </div>
          {pipeline?.console && (
            <p className="text-sm text-muted mt-4">
              <span className="font-medium text-foreground">{pipeline.console.name}</span>
              {" "}— {pipeline.console.features.join(", ")}
            </p>
          )}
        </Panel>
        <Panel title="Readiness">
          <p className="text-body capitalize mb-2">Status: <span className={health?.status === "ready" ? "text-success" : "text-warning"}>{health?.status}</span></p>
          <ul className="space-y-1 text-sm text-muted">
            {health && Object.entries(health.checks).map(([k, v]) => (
              <li key={k}>{k}: {v}</li>
            ))}
          </ul>
        </Panel>
        <Panel title="Configuration">
          <ul className="space-y-1 text-sm">
            <li>Environment: {health?.environment}</li>
            <li>Job queue: {health?.job_queue_running ? "running" : "stopped"}
              {health?.job_queue_backend ? ` (${health.job_queue_backend})` : ""}
              {health?.job_queue_pending != null ? ` · ${health.job_queue_pending} pending` : ""}
            </li>
            <li>WebSocket pub/sub: {health?.ws_pubsub_backend ?? "memory"}</li>
            <li>Redis: {health?.redis_configured ? "configured" : "not configured"}</li>
            <li>Registration: {health?.registration_enabled ? "open" : "closed"}</li>
            <li>Simulation: {health?.simulation_enabled ? "enabled" : "disabled"}</li>
          </ul>
        </Panel>
        <Panel title="Fleet">
          <p className="text-2xl font-semibold">{stats?.hosts_online}/{stats?.hosts_total} hosts online</p>
          <p className="text-sm text-muted mt-2">{stats?.alerts_open} open alerts · {stats?.alerts_critical} critical</p>
          <p className="text-sm text-muted">Retention: {stats?.retention_days} days</p>
        </Panel>
      </div>
    </div>
  );
}
