"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useWebSocket } from "@/lib/websocket";

interface Host {
  id: string;
  name: string;
  hostname: string | null;
  ip_address: string | null;
  os_info: string | null;
  status: string;
  last_seen: string | null;
}

const statusColors: Record<string, string> = {
  online: "bg-green-500",
  offline: "bg-gray-500",
  warning: "bg-yellow-500",
  critical: "bg-red-500",
};

export default function HostsPage() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [name, setName] = useState("");
  const [enrollment, setEnrollment] = useState<{ token: string; install_command: string } | null>(null);
  const [error, setError] = useState("");

  const load = () => api<Host[]>("/api/v1/hosts").then(setHosts).catch(console.error);
  useEffect(() => { load(); }, []);
  useWebSocket((msg) => { if (msg.type === "host_status") load(); });

  async function addHost() {
    if (!name.trim()) return;
    try {
      const host = await api<Host>("/api/v1/hosts", { method: "POST", body: JSON.stringify({ name }) });
      const token = await api<{ token: string; install_command: string }>(
        `/api/v1/hosts/${host.id}/enrollment-token`, { method: "POST" },
      );
      setEnrollment(token);
      setName("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function deleteHost(id: string) {
    if (!confirm("Delete this host?")) return;
    await api(`/api/v1/hosts/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Host Inventory</h1>
      <div className="flex gap-2 mb-6">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Host name"
          className="px-3 py-2 bg-[var(--background)] border border-[var(--border)] rounded flex-1 max-w-xs" />
        <button onClick={addHost} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">Add Host</button>
      </div>
      {error && <p className="text-red-400 mb-4">{error}</p>}
      {enrollment && (
        <div className="mb-6 p-4 bg-blue-900/20 border border-blue-800 rounded">
          <p className="text-sm font-medium mb-2">Enrollment token (shown once):</p>
          <code className="block text-xs break-all mb-3">{enrollment.token}</code>
          <p className="text-sm font-medium mb-2">Install command:</p>
          <code className="block text-xs break-all bg-black/30 p-2 rounded">{enrollment.install_command}</code>
          <button onClick={() => setEnrollment(null)} className="mt-3 text-sm text-gray-400 hover:text-white">Dismiss</button>
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b border-[var(--border)]">
            <th className="pb-2">Name</th><th className="pb-2">Hostname</th><th className="pb-2">IP</th>
            <th className="pb-2">Status</th><th className="pb-2">Last Seen</th><th className="pb-2"></th>
          </tr>
        </thead>
        <tbody>
          {hosts.map((h) => (
            <tr key={h.id} className="border-b border-[var(--border)]/50">
              <td className="py-3">{h.name}</td>
              <td>{h.hostname || "-"}</td>
              <td>{h.ip_address || "-"}</td>
              <td><span className={`inline-block w-2 h-2 rounded-full mr-2 ${statusColors[h.status] || "bg-gray-500"}`} />{h.status}</td>
              <td>{h.last_seen ? new Date(h.last_seen).toLocaleString() : "-"}</td>
              <td><button onClick={() => deleteHost(h.id)} className="text-red-400 hover:text-red-300 text-xs">Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {hosts.length === 0 && <p className="text-gray-500 mt-4">No hosts registered yet.</p>}
    </div>
  );
}
