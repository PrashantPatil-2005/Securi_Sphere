"use client";

import { AlertTriangle, CheckCircle2, HelpCircle, RefreshCw, XCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils/cn";
import type { ComponentHealthResponse, ComponentHealthState, HealthComponent } from "@/lib/types/system";

const STATE_STYLES: Record<ComponentHealthState, { dot: string; text: string; icon: typeof CheckCircle2 }> = {
  healthy: { dot: "bg-success", text: "text-success", icon: CheckCircle2 },
  degraded: { dot: "bg-warning", text: "text-warning", icon: AlertTriangle },
  unavailable: { dot: "bg-danger", text: "text-danger", icon: XCircle },
  unknown: { dot: "bg-muted", text: "text-muted", icon: HelpCircle },
};

function ComponentRow({ component }: { component: HealthComponent }) {
  const style = STATE_STYLES[component.status] ?? STATE_STYLES.unknown;
  const Icon = style.icon;
  return (
    <li className="rounded-lg border border-border-subtle p-3 space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon className={cn("w-4 h-4", style.text)} aria-hidden />
          <span className="text-sm font-medium">{component.name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("text-[11px] font-medium capitalize", style.text)}>{component.status}</span>
          <span className={cn("h-2 w-2 rounded-full", style.dot)} aria-hidden />
        </div>
      </div>
      <p className="text-xs text-muted">{component.message}</p>
      {component.impaired.length > 0 && (
        <p className="text-xs text-warning">Impaired: {component.impaired.join(", ")}</p>
      )}
      {component.next_action && component.status !== "healthy" && (
        <p className="text-xs text-foreground">Next: {component.next_action}</p>
      )}
      <p className="text-[10px] text-muted">
        Last checked: {new Date(component.last_checked).toLocaleString()}
      </p>
    </li>
  );
}

export function ComponentStatusPanel() {
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ["system", "health", "components"],
    queryFn: () => api<ComponentHealthResponse>("/api/v1/system/health/components"),
    refetchInterval: 30_000,
    retry: 1,
  });

  if (isLoading) return <TableSkeleton rows={4} />;

  if (isError || !data) {
    return (
      <Panel title="Component health">
        <QueryError
          message="Component health could not be loaded"
          description="The API did not return component status. Retry to send the same request again."
          onRetry={() => refetch()}
          retrying={isFetching}
        />
        <p className="text-xs text-muted mt-2">
          Detail: {error instanceof Error ? error.message : "unknown error"}
        </p>
      </Panel>
    );
  }

  return (
    <Panel
      title="Component health"
      subtitle={`Overall: ${data.overall} · ${data.environment}`}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-muted">
          Per-dependency status with safe diagnostics. A Redis ping alone never marks the job queue healthy.
        </p>
        <button
          type="button"
          className="btn-ghost text-xs inline-flex items-center gap-1"
          disabled={isFetching}
          onClick={() => refetch()}
        >
          <RefreshCw className={cn("w-3 h-3", isFetching && "animate-spin")} aria-hidden />
          Refresh
        </button>
      </div>
      <ul className="space-y-2">
        {data.components.map((c) => (
          <ComponentRow key={c.id} component={c} />
        ))}
      </ul>
    </Panel>
  );
}
