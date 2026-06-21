"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";

interface Health {
  status: string;
  checks: Record<string, string>;
  environment: string;
  job_queue_running: boolean;
  redis_configured: boolean;
  simulation_enabled: boolean;
  registration_enabled: boolean;
}

interface Stats {
  hosts_total: number;
  hosts_online: number;
  alerts_open: number;
  alerts_critical: number;
  retention_days: number;
}

export default function SystemHealthPage() {
  const { data: health, isLoading: h1 } = useQuery({
    queryKey: ["system", "health"],
    queryFn: () => api<Health>("/api/v1/system/health"),
    refetchInterval: 30_000,
  });
  const { data: stats, isLoading: h2 } = useQuery({
    queryKey: ["system", "stats"],
    queryFn: () => api<Stats>("/api/v1/system/stats"),
    refetchInterval: 30_000,
  });

  if (h1 || h2) return <TableSkeleton rows={6} />;

  return (
    <div className="space-y-6">
      <PageHeader title="System Health" subtitle="Platform readiness and operational metrics (admin)" />
      <div className="grid md:grid-cols-2 gap-6">
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
            <li>Job queue: {health?.job_queue_running ? "running" : "stopped"}</li>
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
