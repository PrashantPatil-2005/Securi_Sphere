"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, LayoutDashboard, Pin, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";

interface SavedSearch {
  id: string;
  name: string;
  query: string;
  alert_enabled: boolean;
  interval_minutes: number;
  created_at: string;
}

interface SavedSearchesPanelProps {
  currentQuery: string;
  onRun: (query: string) => void;
}

export function SavedSearchesPanel({ currentQuery, onRun }: SavedSearchesPanelProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data: saved = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => api<SavedSearch[]>("/api/v1/saved-searches"),
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: (body: { name: string; query: string }) =>
      api<SavedSearch>("/api/v1/saved-searches", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saved-searches"] });
      setName("");
      toast("success", "Saved search created");
    },
    onError: (e: Error) => toast("error", "Save failed", e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, ...body }: { id: string; alert_enabled?: boolean; interval_minutes?: number; name?: string }) =>
      api<SavedSearch>(`/api/v1/saved-searches/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saved-searches"] });
      toast("success", "Saved search updated");
    },
    onError: (e: Error) => toast("error", "Update failed", e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/saved-searches/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saved-searches"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-layout"] });
      toast("success", "Saved search deleted");
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  const pinMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/saved-searches/${id}/pin-dashboard`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-layout"] });
      toast("success", "Pinned to dashboard");
    },
    onError: (e: Error) => toast("error", "Pin failed", e.message),
  });

  function handleSave(e: FormEvent) {
    e.preventDefault();
    const q = currentQuery.trim();
    if (!name.trim() || !q) return;
    createMutation.mutate({ name: name.trim(), query: q });
  }

  return (
    <Panel title="Saved searches" subtitle="Reuse queries, schedule alerts, or pin to your dashboard">
      <form onSubmit={handleSave} className="flex flex-col sm:flex-row gap-2 mb-4">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name this query"
          className="flex-1"
        />
        <Button
          type="submit"
          loading={createMutation.isPending}
          disabled={!name.trim() || !currentQuery.trim()}
          className="shrink-0"
        >
          Save current query
        </Button>
      </form>

      {isLoading && <TableSkeleton rows={3} />}
      {isError && <QueryError onRetry={() => refetch()} />}

      {saved.length === 0 && !isLoading && (
        <p className="text-sm text-muted">No saved searches yet. Run a SIEM query and save it above.</p>
      )}

      <ul className="space-y-2">
        {saved.map((s) => (
          <li key={s.id} className="glass-panel p-3 rounded-lg space-y-2">
            <div className="flex items-start justify-between gap-2">
              <button
                type="button"
                onClick={() => onRun(s.query)}
                className="text-left flex-1 min-w-0 hover:text-accent transition-colors"
              >
                <p className="font-medium truncate">{s.name}</p>
                <p className="font-mono text-xs text-muted truncate mt-0.5">{s.query}</p>
              </button>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  title="Pin to dashboard"
                  onClick={() => pinMutation.mutate(s.id)}
                  loading={pinMutation.isPending}
                >
                  <Pin className="w-4 h-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  title="Delete"
                  onClick={() => deleteMutation.mutate(s.id)}
                >
                  <Trash2 className="w-4 h-4 text-danger" />
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <button
                type="button"
                className={cn(
                  "inline-flex items-center gap-1 px-2 py-1 rounded border",
                  s.alert_enabled ? "border-accent/40 bg-accent/10 text-accent" : "border-border-subtle text-muted",
                )}
                onClick={() => updateMutation.mutate({ id: s.id, alert_enabled: !s.alert_enabled })}
              >
                <Bell className="w-3 h-3" />
                Alerts {s.alert_enabled ? "on" : "off"}
              </button>
              {s.alert_enabled && (
                <label className="inline-flex items-center gap-1 text-muted">
                  Every
                  <Select
                    value={String(s.interval_minutes)}
                    onChange={(e) =>
                      updateMutation.mutate({ id: s.id, interval_minutes: Number(e.target.value) })
                    }
                    className="w-auto min-w-[5rem] py-0.5 text-xs"
                  >
                    {[5, 15, 30, 60, 240].map((m) => (
                      <option key={m} value={m}>
                        {m}m
                      </option>
                    ))}
                  </Select>
                </label>
              )}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="text-xs"
                onClick={() => setEditingId(editingId === s.id ? null : s.id)}
              >
                <LayoutDashboard className="w-3 h-3" />
                Rename
              </Button>
            </div>

            {editingId === s.id && (
              <form
                className="flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  const fd = new FormData(e.currentTarget);
                  const newName = String(fd.get("rename") ?? "").trim();
                  if (!newName) return;
                  updateMutation.mutate({ id: s.id, name: newName });
                  setEditingId(null);
                }}
              >
                <Input name="rename" defaultValue={s.name} className="flex-1" />
                <Button type="submit" size="sm">
                  Save
                </Button>
              </form>
            )}
          </li>
        ))}
      </ul>
    </Panel>
  );
}
