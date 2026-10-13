"use client";

import { useMemo } from "react";
import { AlertTriangle, CheckCircle2, HelpCircle, RefreshCw, XCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { cn } from "@/lib/utils/cn";
import type { SimulationReadiness, ComponentHealthState } from "@/lib/types/system";

const STATE_META: Record<
  ComponentHealthState | "ready" | "blocked",
  { icon: typeof CheckCircle2; textClass: string }
> = {
  ready: { icon: CheckCircle2, textClass: "text-success" },
  healthy: { icon: CheckCircle2, textClass: "text-success" },
  degraded: { icon: AlertTriangle, textClass: "text-warning" },
  blocked: { icon: XCircle, textClass: "text-danger" },
  unavailable: { icon: XCircle, textClass: "text-danger" },
  unknown: { icon: HelpCircle, textClass: "text-muted" },
};

interface OperationalReadinessPanelProps {
  scenarioId: string | null;
  hostId: string | null;
}

/**
 * Demo Center readiness: separates synthetic-injection readiness (backend)
 * from live-host readiness (enrolled agent + required telemetry).
 */
export function OperationalReadinessPanel({ scenarioId, hostId }: OperationalReadinessPanelProps) {
  const query = useQuery({
    queryKey: ["simulation", "readiness", scenarioId, hostId],
    queryFn: () =>
      api<SimulationReadiness>(
        `/api/v1/simulation/readiness?scenario_id=${encodeURIComponent(scenarioId!)}${
          hostId ? `&host_id=${encodeURIComponent(hostId)}` : ""
        }`,
      ),
    enabled: !!scenarioId,
    staleTime: 15_000,
    refetchInterval: 30_000,
    retry: 1,
  });

  const content = useMemo(() => {
    if (!scenarioId) {
      return (
        <p className="text-xs text-muted">
          Select a scenario to check operational readiness.
        </p>
      );
    }
    if (query.isLoading && !query.data) {
      return <p className="text-xs text-muted">Checking readiness&hellip;</p>;
    }
    if (query.isError || !query.data) {
      return (
        <div className="space-y-1.5">
          <p className="text-xs text-danger">Readiness check failed.</p>
          <p className="text-xs text-muted">
            {query.error instanceof Error ? query.error.message : "Unknown error"} — retry to send the same request.
          </p>
        </div>
      );
    }

    const data = query.data;
    const SynthIcon = data.synthetic_ready ? STATE_META.ready.icon : STATE_META.blocked.icon;
    const LiveIcon = !hostId
      ? STATE_META.unknown.icon
      : data.live_ready
        ? STATE_META.ready.icon
        : STATE_META.blocked.icon;

    return (
      <div className="grid md:grid-cols-2 gap-4">
        {/* Synthetic */}
        <div className="rounded-lg border border-border-subtle p-3 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium">Synthetic injection</span>
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "text-[11px] font-medium capitalize",
                  data.synthetic_ready ? "text-success" : "text-danger",
                )}
              >
                {data.synthetic_ready ? "ready" : "blocked"}
              </span>
              <SynthIcon
                className={cn("w-4 h-4", data.synthetic_ready ? "text-success" : "text-danger")}
                aria-hidden
              />
            </div>
          </div>
          <p className="text-xs text-muted">{data.synthetic_note}</p>
          {data.backend.impaired_components.length > 0 && (
            <p className="text-xs text-warning">
              Impaired backend components: {data.backend.impaired_components.join(", ")}
            </p>
          )}
          <p className="text-[10px] text-muted">
            Provenance: synthetic events only — never counted as live traffic.
          </p>
        </div>

        {/* Live host */}
        <div className="rounded-lg border border-border-subtle p-3 space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium">Live host mode</span>
            <div className="flex items-center gap-1.5">
              <span
                className={cn(
                  "text-[11px] font-medium capitalize",
                  !hostId ? "text-muted" : data.live_ready ? "text-success" : "text-danger",
                )}
              >
                {!hostId ? "not configured" : data.live_ready ? "ready" : "blocked"}
              </span>
              <LiveIcon
                className={cn(
                  "w-4 h-4",
                  !hostId ? "text-muted" : data.live_ready ? "text-success" : "text-danger",
                )}
                aria-hidden
              />
            </div>
          </div>
          {data.host ? (
            <div className="text-xs text-muted space-y-0.5">
              <p>
                Host: <span className="font-medium text-foreground">{data.host.name}</span>
                {data.host.os_info ? ` · ${data.host.os_info}` : ""}
              </p>
              <p>
                Enrolled: {data.host.enrolled ? "yes" : "no"} · Heartbeat: {data.host.heartbeat_state}
                {data.host.heartbeat_age_seconds != null &&
                  ` (${Math.round(data.host.heartbeat_age_seconds)}s ago)`}
              </p>
              {data.host.flow_collector_required && (
                <p>
                  Flow collector:{" "}
                  {data.host.flow_collector_active ? (
                    <span className="text-success">active</span>
                  ) : (
                    <span className="text-danger">inactive</span>
                  )}
                </p>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted">No host selected for live mode.</p>
          )}
          {data.live_reasons.length > 0 && (
            <ul className="space-y-0.5">
              {data.live_reasons.map((r) => (
                <li key={r} className="text-xs text-warning">
                  {r}
                </li>
              ))}
            </ul>
          )}
          {data.required_telemetry.length > 0 && (
            <p className="text-[10px] text-muted">
              Required telemetry: {data.required_telemetry.join(", ")}
            </p>
          )}
        </div>
      </div>
    );
  }, [query.data, query.isLoading, query.isError, query.error, scenarioId, hostId]);

  return (
    <Panel
      title="Operational readiness"
      subtitle="Backend vs live-host readiness for this scenario"
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs text-muted">
          Live mode requires an enrolled agent with a recent heartbeat and any required
          telemetry source active. Synthetic readiness is reported separately.
        </p>
        <button
          type="button"
          className="btn-ghost text-xs inline-flex items-center gap-1"
          disabled={query.isFetching}
          onClick={() => query.refetch()}
        >
          <RefreshCw className={cn("w-3 h-3", query.isFetching && "animate-spin")} aria-hidden />
          Refresh
        </button>
      </div>
      {content}
    </Panel>
  );
}
