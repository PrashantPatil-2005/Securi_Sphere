"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Shield } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { useToast } from "@/components/ui/Toast";

interface RefSet {
  id: string;
  name: string;
  description: string | null;
  set_type: string;
  enabled: boolean;
  entry_count: number;
  source_type: "manual" | "feed";
  feed_url: string | null;
  feed_format: "txt" | "csv" | "json" | null;
  feed_last_sync_at: string | null;
  feed_last_sync_status: string | null;
  feed_last_sync_error: string | null;
}

interface RefEntry {
  id: string;
  value: string;
  note: string | null;
}

const SET_TYPES = ["ip", "username", "hostname", "domain", "hash", "port"] as const;

export function ReferenceSetsPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [setType, setSetType] = useState<(typeof SET_TYPES)[number]>("ip");
  const [sourceType, setSourceType] = useState<"manual" | "feed">("manual");
  const [description, setDescription] = useState("");
  const [feedUrl, setFeedUrl] = useState("");
  const [feedFormat, setFeedFormat] = useState<"txt" | "csv" | "json">("txt");
  const [bulkValues, setBulkValues] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);

  const { data: sets = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["reference-sets"],
    queryFn: () => api<RefSet[]>("/api/v1/reference-sets"),
  });

  const { data: entries = [], refetch: refetchEntries } = useQuery({
    queryKey: ["reference-sets", selectedId, "entries"],
    queryFn: () => api<RefEntry[]>(`/api/v1/reference-sets/${selectedId}/entries`),
    enabled: !!selectedId,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api<RefSet>("/api/v1/reference-sets", {
        method: "POST",
        body: JSON.stringify({
          name,
          set_type: setType,
          description: description || null,
          source_type: sourceType,
          feed_url: sourceType === "feed" ? feedUrl || null : null,
          feed_format: sourceType === "feed" ? feedFormat : null,
        }),
      }),
    onSuccess: (data) => {
      toast("success", "Reference set created");
      setName("");
      setDescription("");
      setFeedUrl("");
      setSourceType("manual");
      setFeedFormat("txt");
      setSelectedId(data.id);
      queryClient.invalidateQueries({ queryKey: ["reference-sets"] });
    },
    onError: (e: Error) => toast("error", "Create failed", e.message),
  });

  const updateSetMutation = useMutation({
    mutationFn: (payload: { id: string; description?: string; enabled?: boolean }) =>
      api(`/api/v1/reference-sets/${payload.id}`, {
        method: "PATCH",
        body: JSON.stringify({ description: payload.description, enabled: payload.enabled }),
      }),
    onSuccess: () => {
      toast("success", "Reference set updated");
      queryClient.invalidateQueries({ queryKey: ["reference-sets"] });
    },
    onError: (e: Error) => toast("error", "Update failed", e.message),
  });

  const deleteSetMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/reference-sets/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("success", "Reference set deleted");
      setSelectedId(null);
      queryClient.invalidateQueries({ queryKey: ["reference-sets"] });
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  const syncFeedMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/reference-sets/${id}/sync-feed`, { method: "POST" }),
    onSuccess: () => {
      toast("success", "Feed synchronized");
      queryClient.invalidateQueries({ queryKey: ["reference-sets"] });
      refetchEntries();
    },
    onError: (e: Error) => toast("error", "Feed sync failed", e.message),
  });

  const addEntriesMutation = useMutation({
    mutationFn: () => {
      const values = bulkValues.split(/[\n,]+/).map((v) => v.trim()).filter(Boolean);
      return api(`/api/v1/reference-sets/${selectedId}/entries`, {
        method: "POST",
        body: JSON.stringify({ values }),
      });
    },
    onSuccess: () => {
      toast("success", "Entries added");
      setBulkValues("");
      refetchEntries();
      queryClient.invalidateQueries({ queryKey: ["reference-sets"] });
    },
    onError: (e: Error) => toast("error", "Add failed", e.message),
  });

  const deleteEntryMutation = useMutation({
    mutationFn: (entryId: string) =>
      api(`/api/v1/reference-sets/${selectedId}/entries/${entryId}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("success", "Entry removed");
      refetchEntries();
      queryClient.invalidateQueries({ queryKey: ["reference-sets"] });
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  const selected = sets.find((s) => s.id === selectedId);

  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <>
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <Panel title="Create reference set" subtitle="Named lists for SIEM ref: filters and real-time detection">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate();
            }}
            className="grid gap-3 sm:grid-cols-2"
          >
            <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="bad_ips" className="font-mono" />
            <Select label="Type" value={setType} onChange={(e) => setSetType(e.target.value as typeof setType)}>
              {SET_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </Select>
            <Select label="Source" value={sourceType} onChange={(e) => setSourceType(e.target.value as "manual" | "feed")}>
              <option value="manual">manual</option>
              <option value="feed">feed</option>
            </Select>
            <Input label="Description" value={description} onChange={(e) => setDescription(e.target.value)} className="sm:col-span-2" />
            {sourceType === "feed" && (
              <>
                <Input
                  label="Feed URL"
                  required
                  value={feedUrl}
                  onChange={(e) => setFeedUrl(e.target.value)}
                  placeholder="https://example.com/blocklist.txt"
                  className="sm:col-span-2 font-mono"
                />
                <Select label="Feed format" value={feedFormat} onChange={(e) => setFeedFormat(e.target.value as "txt" | "csv" | "json")}>
                  <option value="txt">txt</option>
                  <option value="csv">csv</option>
                  <option value="json">json</option>
                </Select>
              </>
            )}
            <Button type="submit" loading={createMutation.isPending} className="sm:col-span-2">Create set</Button>
          </form>
        </Panel>
        <Panel title="Reference sets">
          {isLoading ? <TableSkeleton rows={4} /> : sets.length === 0 ? (
            <EmptyState
              title="No reference sets"
              description="Demo data seeds on first startup. Create a set or run Attack Lab to generate detection matches."
              icon={<Shield className="w-8 h-8" />}
              action="/simulation"
              actionLabel="Open Attack Lab"
            />
          ) : (
            <div className="space-y-2">
              {sets.map((s) => (
                <div
                  key={s.id}
                  className={`p-3 rounded border transition-colors ${selectedId === s.id ? "border-accent bg-accent/10" : "border-border-subtle"}`}
                >
                  <button type="button" onClick={() => { setSelectedId(s.id); setEditDesc(s.description ?? ""); }} className="w-full text-left">
                    <div className="flex justify-between gap-2">
                      <span className="font-mono text-accent">{s.name}</span>
                      <span className="text-xs text-muted">{s.entry_count} entries</span>
                    </div>
                    <p className="text-xs text-muted mt-1">
                      {s.set_type} · {s.source_type}{s.description ? ` · ${s.description}` : ""}
                      {!s.enabled && " · disabled"}
                    </p>
                    {s.source_type === "feed" && (
                      <p className="text-xs text-muted mt-1">
                        {s.feed_last_sync_status ? `sync: ${s.feed_last_sync_status}` : "sync: never"}
                        {s.feed_last_sync_at ? ` · ${new Date(s.feed_last_sync_at).toLocaleString()}` : ""}
                      </p>
                    )}
                  </button>
                  <div className="flex gap-2 mt-2">
                    <button
                      type="button"
                      className="btn-ghost text-xs"
                      onClick={() => updateSetMutation.mutate({ id: s.id, enabled: !s.enabled })}
                    >
                      {s.enabled ? "Disable" : "Enable"}
                    </button>
                    {s.source_type === "feed" && (
                      <button
                        type="button"
                        className="btn-ghost text-xs"
                        onClick={() => syncFeedMutation.mutate(s.id)}
                        disabled={syncFeedMutation.isPending}
                      >
                        Sync feed
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-ghost text-xs text-danger"
                      onClick={() => setPendingDelete({ id: s.id, name: s.name })}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>
      <Panel title={selected ? `Entries · ${selected.name}` : "Select a set"} subtitle="Paste values separated by commas or newlines">
        {selected ? (
          <>
            {selected.source_type === "feed" && (
              <div className="mb-4 p-2 rounded border border-border-subtle text-xs text-muted">
                Feed: <span className="font-mono">{selected.feed_url || "n/a"}</span>
                {" · "}
                format: {selected.feed_format || "auto"}
                {" · "}
                status: {selected.feed_last_sync_status || "never"}
                {selected.feed_last_sync_error ? ` · ${selected.feed_last_sync_error}` : ""}
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                updateSetMutation.mutate({ id: selected.id, description: editDesc || undefined });
              }}
              className="flex gap-2 mb-4"
            >
              <Input label="Description" value={editDesc} onChange={(e) => setEditDesc(e.target.value)} className="flex-1" />
              <Button type="submit" className="self-end" loading={updateSetMutation.isPending}>Save</Button>
            </form>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addEntriesMutation.mutate();
              }}
              className="space-y-3 mb-4"
            >
              <textarea
                value={bulkValues}
                onChange={(e) => setBulkValues(e.target.value)}
                placeholder="203.0.113.50&#10;198.51.100.99"
                className="input-siem w-full min-h-[100px] font-mono text-sm"
                aria-label="Bulk values"
              />
              <Button type="submit" loading={addEntriesMutation.isPending} disabled={!bulkValues.trim()}>Add entries</Button>
            </form>
            <div className="space-y-1 max-h-80 overflow-y-auto font-mono text-sm">
              {entries.map((e) => (
                <div key={e.id} className="p-2 rounded bg-[var(--input-bg)] flex justify-between gap-2 items-center">
                  <span>{e.value}</span>
                  <div className="flex items-center gap-2">
                    {e.note && <span className="text-xs text-muted">{e.note}</span>}
                    <button type="button" className="btn-ghost text-xs text-danger" onClick={() => deleteEntryMutation.mutate(e.id)}>Remove</button>
                  </div>
                </div>
              ))}
              {entries.length === 0 && <p className="text-sm text-muted">No entries in this set.</p>}
            </div>
            <p className="text-xs text-muted mt-4">
              SIEM: <code className="text-accent">source_ip:ref:{selected.name}</code>
              {" · "}Detection matches {selected.set_type} fields on ingest.
            </p>
            <Link
              href={`/search?q=${encodeURIComponent(`source_ip:ref:${selected.name}`)}&mode=siem`}
              className="btn-ghost text-xs inline-flex items-center gap-1 mt-2"
            >
              <Search className="w-3 h-3" />
              Test in Search
            </Link>
          </>
        ) : (
          <p className="text-sm text-muted">Select a reference set to manage entries.</p>
        )}
      </Panel>
    </div>
    <ConfirmDialog
      open={!!pendingDelete}
      onClose={() => setPendingDelete(null)}
      onConfirm={() => {
        if (pendingDelete) deleteSetMutation.mutate(pendingDelete.id);
        setPendingDelete(null);
      }}
      title="Delete reference set"
      description={pendingDelete ? `Remove "${pendingDelete.name}" and all its entries? This cannot be undone.` : ""}
      confirmLabel="Delete"
      danger
      loading={deleteSetMutation.isPending}
    />
    </>
  );
}

interface BuildingBlock {
  id: string;
  name: string;
  description: string | null;
  category: string;
  siem_query: string;
  enabled: boolean;
}

export function BuildingBlocksPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", description: "", category: "custom", siem_query: "" });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ description: "", category: "custom", siem_query: "" });
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);

  const { data: blocks = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["building-blocks"],
    queryFn: () => api<BuildingBlock[]>("/api/v1/building-blocks"),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api("/api/v1/building-blocks", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          description: form.description || null,
          category: form.category,
          siem_query: form.siem_query,
        }),
      }),
    onSuccess: () => {
      toast("success", "Building block saved");
      setForm({ name: "", description: "", category: "custom", siem_query: "" });
      queryClient.invalidateQueries({ queryKey: ["building-blocks"] });
    },
    onError: (e: Error) => toast("error", "Save failed", e.message),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: { id: string; description: string; category: string; siem_query: string; enabled?: boolean }) =>
      api(`/api/v1/building-blocks/${payload.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          description: payload.description || null,
          category: payload.category,
          siem_query: payload.siem_query,
          enabled: payload.enabled,
        }),
      }),
    onSuccess: () => {
      toast("success", "Building block updated");
      setEditingId(null);
      queryClient.invalidateQueries({ queryKey: ["building-blocks"] });
    },
    onError: (e: Error) => toast("error", "Update failed", e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api(`/api/v1/building-blocks/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast("success", "Building block deleted");
      queryClient.invalidateQueries({ queryKey: ["building-blocks"] });
    },
    onError: (e: Error) => toast("error", "Delete failed", e.message),
  });

  if (isError) return <QueryError onRetry={() => refetch()} />;

  return (
    <>
    <div className="space-y-6">
      <Panel title="Create building block" subtitle="Reusable SIEM query templates — search only, not detection rules">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="grid gap-3 md:grid-cols-2"
        >
          <Input required label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input label="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
          <Input label="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="md:col-span-2" />
          <Input
            required
            label="SIEM query"
            value={form.siem_query}
            onChange={(e) => setForm({ ...form, siem_query: e.target.value })}
            placeholder="event_type:failed_login source_ip:ref:bad_ips date:24h"
            className="md:col-span-2 font-mono"
          />
          <Button type="submit" loading={createMutation.isPending} className="md:col-span-2">Save block</Button>
        </form>
      </Panel>
      <Panel title="Building blocks">
        {isLoading ? <TableSkeleton rows={4} /> : blocks.length === 0 ? (
          <EmptyState
            title="No building blocks"
            description="Reusable SIEM query templates for search. Demo blocks seed on first startup."
            icon={<Shield className="w-8 h-8" />}
            action="/search"
            actionLabel="Open SIEM Search"
          />
        ) : (
          <div className="space-y-2">
            {blocks.map((b) => (
              <div key={b.id} className="p-3 glass-panel">
                {editingId === b.id ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      updateMutation.mutate({ id: b.id, ...editForm });
                    }}
                    className="space-y-2"
                  >
                    <Input label="Category" value={editForm.category} onChange={(e) => setEditForm({ ...editForm, category: e.target.value })} />
                    <Input label="Description" value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
                    <Input label="SIEM query" value={editForm.siem_query} onChange={(e) => setEditForm({ ...editForm, siem_query: e.target.value })} className="font-mono" />
                    <div className="flex gap-2">
                      <Button type="submit" loading={updateMutation.isPending}>Save</Button>
                      <button type="button" className="btn-ghost text-sm" onClick={() => setEditingId(null)}>Cancel</button>
                    </div>
                  </form>
                ) : (
                  <>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-medium">{b.name}{!b.enabled && <span className="text-xs text-muted ml-2">(disabled)</span>}</p>
                        <p className="text-xs text-muted">{b.category}{b.description ? ` · ${b.description}` : ""}</p>
                      </div>
                      <div className="flex gap-2">
                        <Link href={`/search?q=${encodeURIComponent(b.siem_query)}&mode=siem`} className="btn-ghost text-xs">Run in Search</Link>
                        <button type="button" className="btn-ghost text-xs" onClick={() => { setEditingId(b.id); setEditForm({ description: b.description ?? "", category: b.category, siem_query: b.siem_query }); }}>Edit</button>
                        <button type="button" className="btn-ghost text-xs" onClick={() => updateMutation.mutate({ id: b.id, ...editForm, description: b.description ?? "", category: b.category, siem_query: b.siem_query, enabled: !b.enabled })}>{b.enabled ? "Disable" : "Enable"}</button>
                        <button type="button" className="btn-ghost text-xs text-danger" onClick={() => setPendingDelete({ id: b.id, name: b.name })}>Delete</button>
                      </div>
                    </div>
                    <code className="block mt-2 text-xs text-accent font-mono break-all">{b.siem_query}</code>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
    <ConfirmDialog
      open={!!pendingDelete}
      onClose={() => setPendingDelete(null)}
      onConfirm={() => {
        if (pendingDelete) deleteMutation.mutate(pendingDelete.id);
        setPendingDelete(null);
      }}
      title="Delete building block"
      description={pendingDelete ? `Remove "${pendingDelete.name}"? This cannot be undone.` : ""}
      confirmLabel="Delete"
      danger
      loading={deleteMutation.isPending}
    />
    </>
  );
}
