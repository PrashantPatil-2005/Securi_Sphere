"use client";

import { memo } from "react";
import Link from "next/link";
import { Server, ArrowRight } from "lucide-react";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { LoadingState } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { EmptyState } from "@/components/design-system/EmptyState";

interface RiskyHost {
  host_id: string;
  host_name: string;
  risk_score: number;
}

function riskColor(score: number): string {
  if (score > 70) return "var(--severity-critical)";
  if (score > 40) return "var(--severity-high)";
  if (score > 20) return "var(--severity-medium)";
  return "var(--severity-low)";
}

export const HostRiskPanel = memo(function HostRiskPanel() {
  const { data = [], isLoading, isError, refetch } = useSiemQuery<RiskyHost[]>(
    "top-risky-hosts",
    {},
  );

  if (isLoading) {
    return <LoadingState variant="table" rows={5} />;
  }

  if (isError) {
    return <ErrorState variant="card" title="Failed to load host risk" onRetry={() => refetch()} />;
  }

  if (!data.length) {
    return (
      <EmptyState
        title="No hosts monitored"
        description="Deploy agents to start tracking host risk scores."
        icon={<Server className="w-7 h-7" />}
        action="/hosts"
        actionLabel="Manage hosts"
      />
    );
  }

  return (
    <div>
      <div className="space-y-2">
        {data.slice(0, 6).map((host) => (
          <Link
            key={host.host_id}
            href={`/hosts?highlight=${host.host_id}`}
            className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-[var(--sidebar-hover)] transition-colors group"
          >
            <span className="w-32 truncate text-sm font-medium text-foreground group-hover:text-accent transition-colors">
              {host.host_name}
            </span>
            <div className="flex-1 h-1.5 bg-[var(--input-bg)] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${host.risk_score}%`,
                  backgroundColor: riskColor(host.risk_score),
                }}
              />
            </div>
            <span className="w-8 text-right text-xs font-semibold tabular-nums text-muted">
              {host.risk_score}
            </span>
          </Link>
        ))}
      </div>
      {data.length > 6 && (
        <div className="mt-3 pt-3 border-t border-border-subtle">
          <Link href="/hosts" className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors">
            View all hosts
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      )}
    </div>
  );
});
