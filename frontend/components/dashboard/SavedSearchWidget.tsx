"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import { Panel } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";

interface SavedSearchWidgetProps {
  searchId: string;
}

export function SavedSearchWidget({ searchId }: SavedSearchWidgetProps) {
  const { queryParams } = useTimeRange();

  const { data: saved = [] } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () =>
      api<{ id: string; name: string; query: string }[]>("/api/v1/saved-searches"),
    staleTime: 120_000,
  });

  const search = saved.find((s) => s.id === searchId);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard-saved-search", searchId, search?.query, queryParams],
    queryFn: () =>
      api<{ total_events: number; total_alerts: number }>(
        `/api/v1/search/siem${buildQuery({ q: search!.query }, queryParams)}`,
      ),
    enabled: !!search?.query,
    staleTime: 60_000,
  });

  if (!search) {
    return (
      <Panel title="Saved search" subtitle="Search was removed">
        <p className="text-sm text-muted">This widget references a deleted saved search.</p>
      </Panel>
    );
  }

  return (
    <Panel
      title={search.name}
      subtitle="Pinned SIEM query"
      action={
        <Link
          href={`/search?${new URLSearchParams({ q: search.query, mode: "siem" }).toString()}`}
          className="text-xs text-accent hover:underline"
        >
          Open in Search
        </Link>
      }
    >
      {isLoading && <TableSkeleton rows={2} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {data && (
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center">
            <p className="text-2xl font-semibold tabular-nums text-accent">{data.total_events}</p>
            <p className="text-caption text-muted">Events</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-semibold tabular-nums text-accent">{data.total_alerts}</p>
            <p className="text-caption text-muted">Alerts</p>
          </div>
        </div>
      )}
      <p className="mt-3 font-mono text-xs text-muted break-all">{search.query}</p>
    </Panel>
  );
}
