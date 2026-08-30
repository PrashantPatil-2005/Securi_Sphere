"use client";

import { memo } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { StatusBadge } from "@/components/design-system/Badge";
import { hostStatusColor, hostRiskColor, hostRiskLevel } from "@/lib/types/host";
import type { HostSummary } from "@/lib/types/host";

interface HostDetailHeaderProps {
  host: HostSummary;
}

function formatRelativeTime(ts: string | null): string {
  if (!ts) return "Never";
  const now = Date.now();
  const then = new Date(ts).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function HostDetailHeaderInner({ host }: HostDetailHeaderProps) {
  const riskLevel = hostRiskLevel(host.risk_score);

  return (
    <div className="space-y-4">
      <Link
        href="/hosts"
        className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-3 h-3" />
        Back to Hosts
      </Link>

      <div className="flex items-start gap-4">
        {/* Status dot */}
        <span
          className={`w-3 h-3 rounded-full shrink-0 mt-1.5 ${
            host.status === "online" ? "bg-success" :
            host.status === "critical" ? "bg-danger" :
            host.status === "warning" ? "bg-warning" :
            "bg-muted"
          }`}
        />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-semibold text-foreground">{host.name}</h1>
            <StatusBadge status={host.status} />
            {host.enrolled && (
              <span className="text-[10px] text-success font-medium">Agent Enrolled</span>
            )}
          </div>
          {host.hostname && host.hostname !== host.name && (
            <p className="text-sm text-muted font-mono mt-0.5">{host.hostname}</p>
          )}
          {host.ip_address && (
            <p className="text-xs text-muted font-mono">{host.ip_address}</p>
          )}
        </div>
      </div>

      {/* Quick stats */}
      <div className="flex flex-wrap gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-muted">Risk:</span>
          <span className={`font-mono font-semibold ${hostRiskColor(host.risk_score)}`}>
            {host.risk_score !== null ? `${host.risk_score}/100` : "—"}
          </span>
          {riskLevel !== "none" && (
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
              riskLevel === "critical" ? "bg-danger/15 text-danger" :
              riskLevel === "high" ? "bg-warning/15 text-warning" :
              riskLevel === "medium" ? "bg-severity-medium/15 text-severity-medium" :
              "bg-success/15 text-success"
            }`}>
              {riskLevel.toUpperCase()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted">Status:</span>
          <span className={`capitalize ${hostStatusColor(host.status)}`}>{host.status}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted">Last seen:</span>
          <span className="text-foreground">{formatRelativeTime(host.last_seen)}</span>
        </div>
        {host.os_info && (
          <div className="flex items-center gap-2">
            <span className="text-muted">OS:</span>
            <span className="text-foreground">{host.os_info}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export const HostDetailHeader = memo(HostDetailHeaderInner);
