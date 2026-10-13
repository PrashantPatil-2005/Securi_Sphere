"use client";

import { memo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { useEnrollmentTokenMutation, useHostAgentStatus } from "@/lib/hooks/useHosts";
import { cn } from "@/lib/utils/cn";
import type { HostSummary } from "@/lib/types/host";

interface HostAgentHealthProps {
  host: HostSummary;
  metrics?: {
    cpu_percent: number | null;
    memory_percent: number | null;
    disk_percent: number | null;
    uptime_seconds: number | null;
    recorded_at: string;
  } | null;
  flowStatus?: {
    collector_active: boolean;
    flow_count_24h: number;
    distinct_dst_ports_24h: number;
    last_flow_at: string | null;
  } | null;
}

function formatUptime(seconds: number | null): string {
  if (!seconds) return "—";
  const days = Math.floor(seconds / 86400);
  const hrs = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hrs}h`;
  if (hrs > 0) return `${hrs}h ${mins}m`;
  return `${mins}m`;
}

function HostAgentHealthInner({ host, metrics, flowStatus }: HostAgentHealthProps) {
  const { toast } = useToast();
  const [tokenResult, setTokenResult] = useState<{
    token: string;
    install_command: string;
  } | null>(null);

  const tokenMutation = useEnrollmentTokenMutation({
    onSuccess: (data) => {
      setTokenResult({ token: data.token, install_command: data.install_command });
    },
    onError: (e) => {
      toast("error", "Failed to generate token", e.message);
    },
  });

  const {
    data: agentStatus,
    isLoading: agentStatusLoading,
    refetch: refetchAgentStatus,
    isFetching: agentStatusFetching,
  } = useHostAgentStatus(host.id);

  return (
    <Card>
      <CardHeader title="Agent Health" subtitle="System metrics and agent status" />
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <span className="text-muted">Agent Status</span>
            <p className={`font-medium ${host.enrolled ? "text-success" : "text-muted"}`}>
              {host.enrolled ? "Enrolled" : "Not Enrolled"}
            </p>
          </div>
          <div>
            <span className="text-muted">Status</span>
            <p className="font-medium capitalize">{host.status}</p>
          </div>
          {host.os_info && (
            <div>
              <span className="text-muted">Operating System</span>
              <p className="font-medium">{host.os_info}</p>
            </div>
          )}
          {host.hostname && (
            <div>
              <span className="text-muted">Hostname</span>
              <p className="font-medium font-mono">{host.hostname}</p>
            </div>
          )}
          {host.ip_address && (
            <div>
              <span className="text-muted">IP Address</span>
              <p className="font-medium font-mono">{host.ip_address}</p>
            </div>
          )}
          <div>
            <span className="text-muted">First Seen</span>
            <p className="font-medium">
              {host.created_at ? new Date(host.created_at).toLocaleDateString() : "—"}
            </p>
          </div>
        </div>

        {!host.enrolled && (
          <div className="border-t border-border-subtle pt-3">
            <Button
              variant="primary"
              size="sm"
              onClick={() => tokenMutation.mutate(host.id)}
              loading={tokenMutation.isPending}
            >
              Generate Enrollment Token
            </Button>
          </div>
        )}

        {/* Agent Operations (Phase 9): version, heartbeat, delivery, re-enroll */}
        <div className="border-t border-border-subtle pt-3">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-medium text-muted uppercase tracking-wide">Agent Operations</h4>
            <button
              type="button"
              className="inline-flex items-center gap-1 text-[11px] text-muted hover:text-accent transition-colors"
              disabled={agentStatusFetching}
              onClick={() => refetchAgentStatus()}
            >
              <RefreshCw className={cn("w-3 h-3", agentStatusFetching && "animate-spin")} aria-hidden />
              Refresh
            </button>
          </div>
          {agentStatusLoading && !agentStatus ? (
            <p className="text-xs text-muted">Loading agent status&hellip;</p>
          ) : agentStatus ? (
            <>
              {agentStatus.messages.length > 0 && (
                <ul className="mb-2 space-y-0.5">
                  {agentStatus.messages.map((m) => (
                    <li key={m} className="text-[11px] text-warning">{m}</li>
                  ))}
                </ul>
              )}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-muted">Agent Version</span>
                  <p className="font-medium font-mono">{agentStatus.agent_version ?? "—"}</p>
                </div>
                <div>
                  <span className="text-muted">Heartbeat</span>
                  <p
                    className={cn(
                      "font-medium capitalize",
                      agentStatus.heartbeat_state === "recent" && "text-success",
                      agentStatus.heartbeat_state === "stale" && "text-warning",
                      agentStatus.heartbeat_state === "never" && "text-danger",
                    )}
                  >
                    {agentStatus.heartbeat_state}
                    {agentStatus.heartbeat_age_seconds != null && ` (${Math.round(agentStatus.heartbeat_age_seconds)}s ago)`}
                  </p>
                </div>
                <div>
                  <span className="text-muted">Last Event</span>
                  <p className="font-medium">
                    {agentStatus.last_event_at ? new Date(agentStatus.last_event_at).toLocaleString() : "—"}
                  </p>
                </div>
                <div>
                  <span className="text-muted">Last Metric</span>
                  <p className="font-medium">
                    {agentStatus.last_metric_at ? new Date(agentStatus.last_metric_at).toLocaleString() : "—"}
                  </p>
                </div>
                {agentStatus.integrity_recorded && (
                  <div className="col-span-2">
                    <span className="text-muted">Integrity</span>
                    <p className="font-medium">
                      Hash recorded
                      {agentStatus.agent_hash_changed_at && (
                        <> · changed {new Date(agentStatus.agent_hash_changed_at).toLocaleString()}</>
                      )}
                    </p>
                  </div>
                )}
              </div>

              {agentStatus.delivery_stats && (
                <div className="mt-3 rounded-md border border-border-subtle p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-muted uppercase tracking-wide">Delivery Telemetry</span>
                    <span className="text-[10px] text-muted">
                      from {agentStatus.delivery_stats_source === "agent_heartbeat" ? "agent heartbeat" : "unknown source"}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
                    <div>
                      <span className="text-muted">Buffered</span>
                      <p className="font-medium tabular-nums">{agentStatus.delivery_stats.buffered_events ?? "—"}</p>
                    </div>
                    <div>
                      <span className="text-muted">Dropped</span>
                      <p
                        className={cn(
                          "font-medium tabular-nums",
                          (agentStatus.delivery_stats.dropped_events ?? 0) > 0 && "text-warning",
                        )}
                      >
                        {agentStatus.delivery_stats.dropped_events ?? "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted">Consecutive Failures</span>
                      <p
                        className={cn(
                          "font-medium tabular-nums",
                          (agentStatus.delivery_stats.consecutive_failures ?? 0) > 0 && "text-warning",
                        )}
                      >
                        {agentStatus.delivery_stats.consecutive_failures ?? "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted">Auth</span>
                      <p className={cn("font-medium", agentStatus.delivery_stats.auth_failed && "text-danger")}>
                        {agentStatus.delivery_stats.auth_failed ? "failing" : "ok"}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted">Last Flush</span>
                      <p className="font-medium">
                        {agentStatus.delivery_stats.last_flush_at
                          ? new Date(agentStatus.delivery_stats.last_flush_at).toLocaleString()
                          : "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted">Last Success</span>
                      <p className="font-medium">
                        {agentStatus.delivery_stats.last_success_at
                          ? new Date(agentStatus.delivery_stats.last_success_at).toLocaleString()
                          : "—"}
                      </p>
                    </div>
                  </div>
                  {agentStatus.delivery_stats.flows_enabled !== undefined && (
                    <p className="text-[11px] text-muted">
                      Flow collector on agent: {agentStatus.delivery_stats.flows_enabled ? "enabled" : "disabled"}
                    </p>
                  )}
                </div>
              )}

              {!agentStatus.delivery_stats && (
                <p className="text-[11px] text-muted mt-2">
                  No delivery telemetry yet — the agent reports it with each heartbeat.
                </p>
              )}

              <div className="mt-3">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => tokenMutation.mutate(host.id)}
                  loading={tokenMutation.isPending}
                >
                  {agentStatus.enrolled ? "Generate Re-enrollment Token" : "Generate Enrollment Token"}
                </Button>
              </div>
            </>
          ) : (
            <p className="text-xs text-muted">
              Agent status unavailable. The host detail API may not include the agent-status endpoint.
            </p>
          )}
        </div>

        {metrics && (
          <>
            <div className="border-t border-border-subtle pt-3">
              <h4 className="text-xs font-medium text-muted uppercase tracking-wide mb-2">System Metrics</h4>
              <div className="grid grid-cols-2 gap-3 text-xs">
                {metrics.cpu_percent !== null && (
                  <div>
                    <span className="text-muted">CPU</span>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-card-elevated overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(metrics.cpu_percent, 100)}%`,
                            backgroundColor: metrics.cpu_percent > 90 ? "var(--danger)" : metrics.cpu_percent > 70 ? "var(--warning)" : "var(--success)",
                          }}
                        />
                      </div>
                      <span className="tabular-nums w-10 text-right">{metrics.cpu_percent.toFixed(1)}%</span>
                    </div>
                  </div>
                )}
                {metrics.memory_percent !== null && (
                  <div>
                    <span className="text-muted">Memory</span>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-card-elevated overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(metrics.memory_percent, 100)}%`,
                            backgroundColor: metrics.memory_percent > 90 ? "var(--danger)" : metrics.memory_percent > 70 ? "var(--warning)" : "var(--success)",
                          }}
                        />
                      </div>
                      <span className="tabular-nums w-10 text-right">{metrics.memory_percent.toFixed(1)}%</span>
                    </div>
                  </div>
                )}
                {metrics.disk_percent !== null && (
                  <div>
                    <span className="text-muted">Disk</span>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full bg-card-elevated overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(metrics.disk_percent, 100)}%`,
                            backgroundColor: metrics.disk_percent > 85 ? "var(--danger)" : metrics.disk_percent > 70 ? "var(--warning)" : "var(--success)",
                          }}
                        />
                      </div>
                      <span className="tabular-nums w-10 text-right">{metrics.disk_percent.toFixed(1)}%</span>
                    </div>
                  </div>
                )}
                {metrics.uptime_seconds !== null && (
                  <div>
                    <span className="text-muted">Uptime</span>
                    <p className="font-medium tabular-nums">{formatUptime(metrics.uptime_seconds)}</p>
                  </div>
                )}
              </div>
            </div>
            <p className="text-[10px] text-muted">
              Last updated: {new Date(metrics.recorded_at).toLocaleString()}
            </p>
          </>
        )}

        {!metrics && (
          <div className="border-t border-border-subtle pt-3">
            <p className="text-xs text-muted">System metrics unavailable.</p>
          </div>
        )}

        {flowStatus && (
          <div className="border-t border-border-subtle pt-3">
            <h4 className="text-xs font-medium text-muted uppercase tracking-wide mb-2">Flow Collector</h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-muted">Status</span>
                <p className={`font-medium ${flowStatus.collector_active ? "text-success" : "text-muted"}`}>
                  {flowStatus.collector_active ? "Active" : "Idle"}
                </p>
              </div>
              <div>
                <span className="text-muted">Flows (24h)</span>
                <p className="font-medium tabular-nums">{flowStatus.flow_count_24h}</p>
              </div>
              <div>
                <span className="text-muted">Distinct Dst Ports (24h)</span>
                <p className="font-medium tabular-nums">{flowStatus.distinct_dst_ports_24h}</p>
              </div>
              <div>
                <span className="text-muted">Last Flow</span>
                <p className="font-medium">
                  {flowStatus.last_flow_at ? new Date(flowStatus.last_flow_at).toLocaleString() : "—"}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Enrollment Token Dialog */}
      <Dialog
        open={!!tokenResult}
        onClose={() => { setTokenResult(null); }}
        title="Enrollment Token"
        description="Copy this token and run the install command on the target host."
      >
        {tokenResult && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted block mb-1">Enrollment Token</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs font-mono bg-card-elevated px-3 py-2 rounded border border-border-subtle break-all">
                  {tokenResult.token}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(tokenResult.token);
                    toast("success", "Copied", "Token copied to clipboard.");
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted block mb-1">Install Command (Linux)</label>
              <div className="flex items-start gap-2">
                <pre className="flex-1 text-xs font-mono bg-card-elevated px-3 py-2 rounded border border-border-subtle overflow-x-auto whitespace-pre-wrap break-all">
                  {tokenResult.install_command}
                </pre>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(tokenResult.install_command);
                    toast("success", "Copied", "Install command copied to clipboard.");
                  }}
                >
                  Copy
                </Button>
              </div>
              <p className="text-[10px] text-muted mt-1">Run this on the target Linux host with sudo privileges.</p>
            </div>
            <div className="flex justify-end">
              <Button variant="primary" onClick={() => setTokenResult(null)}>
                Done
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </Card>
  );
}

export const HostAgentHealth = memo(HostAgentHealthInner);
