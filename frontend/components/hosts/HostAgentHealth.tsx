"use client";

import { memo, useState } from "react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { useEnrollmentTokenMutation } from "@/lib/hooks/useHosts";
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

function HostAgentHealthInner({ host, metrics }: HostAgentHealthProps) {
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
