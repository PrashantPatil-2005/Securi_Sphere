"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";

interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  created_at: string;
}

export default function IncidentsPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["incidents"],
    queryFn: () => api<Incident[]>("/api/v1/incidents"),
  });

  const createMutation = useMutation({
    mutationFn: () => api("/api/v1/incidents", { method: "POST", body: JSON.stringify({ title, description: desc, severity: "medium" }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      setTitle("");
      setDesc("");
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/incidents/${id}/status?status=${status}`, { method: "PATCH" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["incidents"] }),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Investigations" subtitle="Incident tracking and status workflow" />
      {isLoading && <TableSkeleton rows={4} />}
      <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="panel p-4 flex gap-3 flex-wrap">
        <input required placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} className="input-siem flex-1 min-w-[200px]" />
        <input placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)} className="input-siem flex-1 min-w-[200px]" />
        <button type="submit" className="btn-primary">Create</button>
      </form>
      <Panel title="Incidents">
      <div className="space-y-3">
        {items.map((i) => (
          <div key={i.id} className="p-4 border border-border-subtle rounded-lg">
            <div className="flex justify-between items-start">
              <div>
                <span className={`text-xs severity-${i.severity} uppercase font-bold mr-2`}>{i.severity}</span>
                <span className="font-medium">{i.title}</span>
                <span className="text-xs text-muted ml-2 capitalize">{i.status}</span>
                {i.description && <p className="text-sm text-muted mt-1">{i.description}</p>}
              </div>
              {i.status === "open" && (
                <div className="flex gap-2">
                  <button type="button" onClick={() => statusMutation.mutate({ id: i.id, status: "investigating" })} className="btn-ghost text-xs">Investigate</button>
                  <button type="button" onClick={() => statusMutation.mutate({ id: i.id, status: "resolved" })} className="btn-ghost text-xs">Resolve</button>
                </div>
              )}
            </div>
          </div>
        ))}
        {!isLoading && items.length === 0 && <p className="text-muted">No incidents.</p>}
      </div>
      </Panel>
    </div>
  );
}
