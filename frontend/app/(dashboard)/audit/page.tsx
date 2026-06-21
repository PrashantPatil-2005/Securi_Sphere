"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { VirtualList } from "@/components/VirtualList";
import { rowKeyById } from "@/lib/rowKey";

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
    <div className="grid grid-cols-[minmax(140px,1fr)_minmax(120px,1fr)_minmax(140px,1fr)_100px_1fr] gap-3 py-2 border-b border-[var(--border)]/50 text-sm items-start">
      <span className="text-gray-400 whitespace-nowrap">{new Date(entry.timestamp).toLocaleString()}</span>
      <span className="font-mono text-blue-400">{entry.action}</span>
      <span>{entry.resource_type}{entry.resource_id ? ` / ${entry.resource_id.slice(0, 8)}...` : ""}</span>
      <span className="text-gray-500">{entry.ip_address || "-"}</span>
      <span className="text-gray-500 truncate">{entry.details ? JSON.stringify(entry.details) : "-"}</span>
    </div>
  );
}

export default function AuditPage() {
  const [filter, setFilter] = useState("");
  const debouncedFilter = useDebounce(filter, 400);

  const { data: logs = [] } = useQuery({
    queryKey: ["audit", debouncedFilter],
    queryFn: async () => {
      const q = debouncedFilter ? `?action=${encodeURIComponent(debouncedFilter)}` : "";
      return api<AuditEntry[]>(`/api/v1/audit${q}`);
    },
    staleTime: 30_000,
  });

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Audit Log</h1>
      <input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter by action..."
        className="mb-4 px-3 py-2 bg-[var(--card)] border border-[var(--border)] rounded w-64 text-sm"
      />
      <div className="text-left text-gray-500 border-b border-[var(--border)] grid grid-cols-[minmax(140px,1fr)_minmax(120px,1fr)_minmax(140px,1fr)_100px_1fr] gap-3 py-2 text-xs uppercase">
        <span>Time</span>
        <span>Action</span>
        <span>Resource</span>
        <span>IP</span>
        <span>Details</span>
      </div>
      {logs.length === 0 ? (
        <p className="text-gray-500 mt-4">No audit entries (admin only).</p>
      ) : (
        <VirtualList
          items={logs}
          rowKey={rowKeyById}
          renderItem={(entry) => <AuditRow entry={entry} />}
          height={560}
          estimateSize={44}
        />
      )}
    </div>
  );
}
