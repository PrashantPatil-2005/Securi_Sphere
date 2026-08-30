"use client";

import { memo, useCallback } from "react";
import Link from "next/link";

import { hostStatusColor, hostRiskColor } from "@/lib/types/host";
import type { HostSummary } from "@/lib/types/host";

interface HostRowProps {
  host: HostSummary;
  selected: boolean;
  onClick: (host: HostSummary) => void;
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

function HostRowInner({ host, selected, onClick }: HostRowProps) {
  const handleClick = useCallback(() => onClick(host), [host, onClick]);

  return (
    <Link
      href={`/hosts/${host.id}`}
      onClick={handleClick}
      className={`block w-full text-left px-3 py-2.5 border-b border-border-subtle hover:bg-[var(--sidebar-hover)] transition-colors ${
        selected ? "bg-accent/5 border-l-2 border-l-accent" : "border-l-2 border-l-transparent"
      }`}
    >
      <div className="flex items-center gap-3">
        {/* Status dot */}
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${
            host.status === "online" ? "bg-success" :
            host.status === "critical" ? "bg-danger" :
            host.status === "warning" ? "bg-warning" :
            "bg-muted"
          }`}
          title={host.status}
        />

        {/* Host name + hostname */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-foreground truncate">{host.name}</span>
            {host.hostname && host.hostname !== host.name && (
              <span className="text-[10px] text-muted font-mono truncate hidden sm:block">{host.hostname}</span>
            )}
          </div>
          {host.ip_address && (
            <span className="text-[10px] text-muted font-mono">{host.ip_address}</span>
          )}
        </div>

        {/* Status */}
        <span className={`text-xs capitalize shrink-0 ${hostStatusColor(host.status)}`}>
          {host.status}
        </span>

        {/* Risk score */}
        <span className={`text-xs tabular-nums font-mono shrink-0 w-10 text-right ${hostRiskColor(host.risk_score)}`}>
          {host.risk_score !== null ? host.risk_score : "—"}
        </span>

        {/* Agent */}
        <span className={`text-[10px] shrink-0 w-16 text-right ${host.enrolled ? "text-success" : "text-muted"}`}>
          {host.enrolled ? "Enrolled" : "Pending"}
        </span>

        {/* Alerts */}
        <span className="text-xs tabular-nums shrink-0 w-10 text-right text-muted">
          {host.alert_count ?? 0}
        </span>

        {/* Last seen */}
        <span className="text-[10px] text-muted tabular-nums shrink-0 w-20 text-right hidden md:block">
          {formatRelativeTime(host.last_seen)}
        </span>
      </div>
    </Link>
  );
}

export const HostRow = memo(HostRowInner);
