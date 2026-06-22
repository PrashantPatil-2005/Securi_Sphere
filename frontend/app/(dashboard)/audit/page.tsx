"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { VirtualList } from "@/components/VirtualList";
import { rowKeyById } from "@/lib/rowKey";
import { PageHeader } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/Panel";

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  timestamp: string;
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  return (
    <div className="grid grid-cols-[minmax(140px,1fr)_minmax(120px,1fr)_minmax(140px,1fr)_100px_1fr] gap-3 py-2 border-b border-border-subtle/50 text-sm items-start">
      <span className="text-muted whitespace-nowrap tabular-nums">{new Date(entry.timestamp).toLocaleString()}</span>
      <span className="font-mono text-accent">{entry.action}</span>
      <span>{entry.resource_type}{entry.resource_id ? ` / ${entry.resource_id.slice(0, 8)}…` : ""}</span>
      <span className="text-muted">{entry.ip_address || "—"}</span>
      <span className="text-muted truncate">{entry.details ? JSON.stringify(entry.details) : "—"}</span>
    </div>
  );
}

export default function AuditPage() {
  const [filter, setFilter] = useState("");
  const debouncedFilter = useDebounce(filter, 400);

  const { data: logs = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["audit", debouncedFilter],
    queryFn: async () => {
      const q = debouncedFilter ? `?action=${encodeURIComponent(debouncedFilter)}` : "";
      return api<AuditEntry[]>(`/api/v1/audit${q}`);
    },
    staleTime: 30_000,
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Audit Log" subtitle="Administrative actions and security-relevant changes" />
      <input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter by action…"
        className="input-siem max-w-xs"
      />
      {isLoading && <TableSkeleton rows={8} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {!isLoading && !isError && logs.length === 0 && (
        <EmptyState title="No audit entries" description="Actions will appear here as users interact with the platform." />
      )}
      {!isLoading && !isError && logs.length > 0 && (
        <>
          <div className="text-left text-muted border-b border-border-subtle grid grid-cols-[minmax(140px,1fr)_minmax(120px,1fr)_minmax(140px,1fr)_100px_1fr] gap-3 py-2 text-xs uppercase tracking-wide">
            <span>Time</span>
            <span>Action</span>
            <span>Resource</span>
            <span>IP</span>
            <span>Details</span>
          </div>
          <VirtualList
            items={logs}
            rowKey={rowKeyById}
            height={Math.min(720, logs.length * 44 + 8)}
            estimateSize={44}
            renderItem={(entry) => <AuditRow entry={entry} />}
          />
        </>
      )}
    </div>
  );
}
