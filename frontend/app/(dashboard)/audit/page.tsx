"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  timestamp: string;
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState("");

  const load = () => {
    const q = filter ? `?action=${encodeURIComponent(filter)}` : "";
    api<AuditEntry[]>(`/api/v1/audit${q}`).then(setLogs).catch(console.error);
  };

  useEffect(() => { load(); }, [filter]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Audit Log</h1>
      <input
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter by action..."
        className="mb-4 px-3 py-2 bg-[var(--card)] border border-[var(--border)] rounded w-64 text-sm"
      />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-[var(--border)]">
              <th className="py-2 pr-4">Time</th>
              <th className="py-2 pr-4">Action</th>
              <th className="py-2 pr-4">Resource</th>
              <th className="py-2 pr-4">IP</th>
              <th className="py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-b border-[var(--border)]/50">
                <td className="py-2 pr-4 text-gray-400 whitespace-nowrap">{new Date(l.timestamp).toLocaleString()}</td>
                <td className="py-2 pr-4 font-mono text-blue-400">{l.action}</td>
                <td className="py-2 pr-4">{l.resource_type}{l.resource_id ? ` / ${l.resource_id.slice(0, 8)}...` : ""}</td>
                <td className="py-2 pr-4 text-gray-500">{l.ip_address || "-"}</td>
                <td className="py-2 text-gray-500 truncate max-w-xs">{l.details ? JSON.stringify(l.details) : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && <p className="text-gray-500 mt-4">No audit entries (admin only).</p>}
      </div>
    </div>
  );
}
