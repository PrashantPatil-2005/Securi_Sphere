"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  created_at: string;
}

export default function IncidentsPage() {
  const [items, setItems] = useState<Incident[]>([]);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");

  const load = () => api<Incident[]>("/api/v1/incidents").then(setItems).catch(console.error);
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/incidents", { method: "POST", body: JSON.stringify({ title, description: desc, severity: "medium" }) });
    setTitle("");
    setDesc("");
    load();
  }

  async function setStatus(id: string, status: string) {
    await api(`/api/v1/incidents/${id}/status?status=${status}`, { method: "PATCH" });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Incidents</h1>
      <form onSubmit={create} className="mb-6 p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg flex gap-3">
        <input required placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)}
          className="flex-1 px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm" />
        <input placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)}
          className="flex-1 px-3 py-2 bg-black/30 border border-[var(--border)] rounded text-sm" />
        <button type="submit" className="px-4 py-2 bg-blue-600 rounded text-sm">Create</button>
      </form>
      <div className="space-y-3">
        {items.map((i) => (
          <div key={i.id} className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
            <div className="flex justify-between items-start">
              <div>
                <span className={`text-xs severity-${i.severity} uppercase font-bold mr-2`}>{i.severity}</span>
                <span className="font-medium">{i.title}</span>
                <span className="text-xs text-gray-500 ml-2 capitalize">{i.status}</span>
                {i.description && <p className="text-sm text-gray-400 mt-1">{i.description}</p>}
              </div>
              {i.status === "open" && (
                <div className="flex gap-2">
                  <button onClick={() => setStatus(i.id, "investigating")} className="text-xs px-2 py-1 bg-yellow-900/30 text-yellow-400 rounded">Investigate</button>
                  <button onClick={() => setStatus(i.id, "resolved")} className="text-xs px-2 py-1 bg-green-900/30 text-green-400 rounded">Resolve</button>
                </div>
              )}
            </div>
          </div>
        ))}
        {items.length === 0 && <p className="text-gray-500">No incidents.</p>}
      </div>
    </div>
  );
}
