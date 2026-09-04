"use client";

import { memo } from "react";
import Link from "next/link";
import { Shield, ArrowRight } from "lucide-react";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { SeverityBadge } from "@/components/design-system";
import { LoadingState } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { EmptyState } from "@/components/design-system/EmptyState";

interface AttackTimeline {
  id: string;
  host_name: string;
  title: string;
  risk_level: string;
}

export const AttackTimelines = memo(function AttackTimelines() {
  const { data: rawData, isLoading, isError, refetch } = useSiemQuery<AttackTimeline[]>(
    "attack-timelines",
    {},
  );
  const data = rawData ?? [];

  if (isLoading && !rawData) {
    return <LoadingState variant="table" rows={4} />;
  }

  if (isError && !rawData) {
    return <ErrorState variant="card" title="Failed to load timelines" onRetry={() => refetch()} />;
  }

  if (!data.length) {
    return (
      <EmptyState
        title="No active timelines"
        description="Attack timelines appear when correlated events are detected."
        icon={<Shield className="w-7 h-7" />}
      />
    );
  }

  return (
    <div>
      <div className="space-y-1">
        {data.slice(0, 5).map((t) => (
          <Link
            key={t.id}
            href={`/timeline?timeline=${t.id}`}
            className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-md hover:bg-[var(--sidebar-hover)] transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate group-hover:text-accent transition-colors">
                {t.title}
              </p>
              <p className="text-[11px] text-muted mt-0.5">{t.host_name}</p>
            </div>
            <SeverityBadge severity={t.risk_level} />
          </Link>
        ))}
      </div>
      {data.length > 5 && (
        <div className="mt-3 pt-3 border-t border-border-subtle">
          <Link href="/timeline" className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-accent transition-colors">
            View all timelines
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      )}
    </div>
  );
});
