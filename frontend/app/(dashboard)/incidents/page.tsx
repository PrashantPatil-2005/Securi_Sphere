"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ClipboardList } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { InvestigationTrail } from "@/components/InvestigationTrail";
import { useToast } from "@/components/ui/Toast";

interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  host_id: string | null;
  created_at: string;
}

interface IncidentDetail extends Incident {
  notes: { id: string; content: string; user_id: string; created_at: string }[];
  alert_ids: string[];
}

export default function IncidentsPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={6} />}>
      <IncidentsPageContent />
    </Suspense>
  );
}

function IncidentsPageContent() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(searchParams.get("selected"));
  const [note, setNote] = useState("");

  useEffect(() => {
    const id = searchParams.get("selected");
    if (id) setSelectedId(id);
  }, [searchParams]);

  const { data: items = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["incidents"],
    queryFn: () => api<Incident[]>("/api/v1/incidents"),
  });

  const { data: detail, isLoading: detailLoading, isError: detailError, refetch: refetchDetail } = useQuery({
    queryKey: ["incidents", selectedId],
    queryFn: () => api<IncidentDetail>(`/api/v1/incidents/${selectedId}`),
    enabled: !!selectedId,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api("/api/v1/incidents", {
        method: "POST",
        body: JSON.stringify({ title, description: desc, severity: "medium" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      setTitle("");
      setDesc("");
      toast("success", "Incident created");
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/incidents/${id}/status?status=${status}`, { method: "PATCH" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      if (selectedId) queryClient.invalidateQueries({ queryKey: ["incidents", selectedId] });
    },
  });

  const noteMutation = useMutation({
    mutationFn: () =>
      api(`/api/v1/incidents/${selectedId}/notes`, {
        method: "POST",
        body: JSON.stringify({ content: note }),
      }),
    onSuccess: () => {
      setNote("");
      queryClient.invalidateQueries({ queryKey: ["incidents", selectedId] });
      toast("success", "Note added");
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Investigations" subtitle="Incident tracking, notes, and resolution workflow" />
      <InvestigationTrail />
      {isError && <QueryError onRetry={() => refetch()} />}
      {isLoading && !isError && <TableSkeleton rows={4} />}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          createMutation.mutate();
        }}
        className="panel p-4 flex gap-3 flex-wrap"
      >
        <input required placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} className="input-siem flex-1 min-w-[200px]" />
        <input placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)} className="input-siem flex-1 min-w-[200px]" />
        <button type="submit" className="btn-primary" disabled={createMutation.isPending}>
          Create
        </button>
      </form>
      <div className="grid lg:grid-cols-2 gap-6">
        <Panel title="Incidents">
          <div className="space-y-2 max-h-[32rem] overflow-y-auto">
            {!isError && items.map((i) => (
              <button
                key={i.id}
                type="button"
                onClick={() => setSelectedId(i.id)}
                className={`w-full text-left p-4 border rounded-lg transition-colors ${selectedId === i.id ? "border-accent bg-accent/10" : "border-border-subtle hover:bg-[var(--sidebar-hover)]"}`}
              >
                <div className="flex justify-between items-start gap-2">
                  <div>
                    <span className={`text-xs severity-${i.severity} uppercase font-bold mr-2`}>{i.severity}</span>
                    <span className="font-medium">{i.title}</span>
                    <span className="text-xs text-muted ml-2 capitalize">{i.status}</span>
                    {i.description && <p className="text-sm text-muted mt-1 line-clamp-2">{i.description}</p>}
                  </div>
                </div>
              </button>
            ))}
            {!isLoading && !isError && items.length === 0 && (
              <EmptyState
                title="No incidents"
                description="Use the form above to create an incident and begin an investigation."
                icon={<ClipboardList className="w-10 h-10 opacity-40" />}
              />
            )}
          </div>
        </Panel>
        <Panel title="Investigation workspace">
          {detailError && selectedId && <QueryError onRetry={() => refetchDetail()} />}
          {detailLoading && !detailError && <TableSkeleton rows={4} />}
          {detail && !detailLoading && !detailError && (
            <>
              <h2 className="font-semibold text-lg">{detail.title}</h2>
              <p className="text-sm text-muted mb-4 capitalize">{detail.status} · {detail.severity}</p>
              {detail.description && <p className="text-sm mb-4">{detail.description}</p>}
              <div className="flex flex-wrap gap-2 mb-4">
                {detail.status === "open" && (
                  <>
                    <button type="button" onClick={() => statusMutation.mutate({ id: detail.id, status: "investigating" })} className="btn-ghost text-xs">
                      Investigate
                    </button>
                    <button type="button" onClick={() => statusMutation.mutate({ id: detail.id, status: "resolved" })} className="btn-ghost text-xs">
                      Resolve
                    </button>
                  </>
                )}
                {detail.status === "investigating" && (
                  <button type="button" onClick={() => statusMutation.mutate({ id: detail.id, status: "resolved" })} className="btn-ghost text-xs">
                    Resolve
                  </button>
                )}
              </div>
              {detail.alert_ids.length > 0 && (
                <div className="mb-4">
                  <p className="text-caption normal-case text-muted mb-2">Linked alerts</p>
                  <div className="flex flex-wrap gap-2">
                    {detail.alert_ids.map((id) => (
                      <a key={id} href={`/alerts?q=${id.slice(0, 8)}`} className="text-xs font-mono text-accent hover:underline">
                        {id.slice(0, 8)}…
                      </a>
                    ))}
                  </div>
                </div>
              )}
              <div className="space-y-2 mb-4 max-h-48 overflow-y-auto">
                {detail.notes.map((n) => (
                  <div key={n.id} className="p-2 rounded bg-[var(--input-bg)] text-sm">
                    <p>{n.content}</p>
                    <p className="text-[11px] text-muted mt-1">{new Date(n.created_at).toLocaleString()}</p>
                  </div>
                ))}
                {detail.notes.length === 0 && <p className="text-sm text-muted">No analyst notes yet.</p>}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (note.trim()) noteMutation.mutate();
                }}
                className="flex gap-2"
              >
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Add investigation note…" className="input-siem flex-1" />
                <button type="submit" className="btn-primary text-sm" disabled={noteMutation.isPending}>
                  Add
                </button>
              </form>
            </>
          )}
          {!selectedId && !detailLoading && !detailError && <EmptyState title="Select an incident" description="Choose an incident to review notes and linked alerts." />}
        </Panel>
      </div>
    </div>
  );
}
