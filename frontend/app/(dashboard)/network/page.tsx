"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Node { id: string; label: string; type: string; status: string; threat_score?: number; ip?: string; }
interface Edge { from: string; to: string; }

export default function NetworkPage() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  useEffect(() => {
    api<{ nodes: Node[]; edges: Edge[] }>("/api/v1/network/topology").then((r) => {
      setNodes(r.nodes);
      setEdges(r.edges);
    }).catch(console.error);
  }, []);

  const hosts = nodes.filter((n) => n.type === "host");
  const server = nodes.find((n) => n.type === "server");

  function nodeColor(n: Node) {
    if (n.type === "server") return "border-blue-500 bg-blue-900/30";
    if (n.status === "critical" || (n.threat_score ?? 0) >= 70) return "border-red-500 bg-red-900/30";
    if (n.status === "warning" || (n.threat_score ?? 0) >= 40) return "border-yellow-500 bg-yellow-900/20";
    if (n.status === "online") return "border-green-500 bg-green-900/20";
    return "border-gray-600 bg-gray-900/30";
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Network Topology</h1>
      <div className="relative p-8 bg-[var(--card)] border border-[var(--border)] rounded-lg min-h-[400px]">
        {server && (
          <div className="flex justify-center mb-12">
            <div className={`px-6 py-4 rounded-lg border-2 text-center ${nodeColor(server)}`}>
              <div className="font-bold">{server.label}</div>
              <div className="text-xs text-gray-400">Central SIEM</div>
            </div>
          </div>
        )}
        <div className="flex flex-wrap justify-center gap-6">
          {hosts.map((h) => (
            <div key={h.id} className={`px-4 py-3 rounded-lg border-2 text-center min-w-[140px] ${nodeColor(h)}`}>
              <div className="font-medium">{h.label}</div>
              <div className="text-xs text-gray-400 capitalize">{h.status}</div>
              {h.ip && <div className="text-xs text-gray-500">{h.ip}</div>}
              {h.threat_score != null && h.threat_score > 0 && (
                <div className="text-xs text-red-400 mt-1">Threat: {h.threat_score}</div>
              )}
            </div>
          ))}
        </div>
        {hosts.length === 0 && <p className="text-center text-gray-500">No hosts enrolled yet.</p>}
        <p className="text-xs text-gray-600 text-center mt-8">{edges.length} connection(s) to server</p>
      </div>
    </div>
  );
}
