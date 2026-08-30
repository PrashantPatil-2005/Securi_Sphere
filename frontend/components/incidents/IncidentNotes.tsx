"use client";

import { useState, useCallback } from "react";
import { useToast } from "@/components/ui/Toast";
import { useIncidentAddNoteMutation } from "@/lib/hooks/useIncidents";
import type { IncidentNote } from "@/lib/types/incident";

interface Props {
  incidentId: string;
  notes: IncidentNote[];
}

export function IncidentNotes({ incidentId, notes }: Props) {
  const { toast } = useToast();
  const [note, setNote] = useState("");

  const noteMutation = useIncidentAddNoteMutation({
    onSuccess: () => {
      setNote("");
      toast("success", "Note added");
    },
    onError: (e) => toast("error", "Failed to add note", e.message),
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (note.trim()) {
        noteMutation.mutate({ id: incidentId, content: note.trim() });
      }
    },
    [note, incidentId, noteMutation],
  );

  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <h3 className="text-sm font-semibold mb-3">Analyst Notes ({notes.length})</h3>

      <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
        {notes.length === 0 && (
          <p className="text-xs text-muted">No notes yet. Add an investigation note below.</p>
        )}
        {notes.map((n) => (
          <div key={n.id} className="p-2 rounded-lg bg-surface-elevated text-sm">
            <p>{n.content}</p>
            <p className="text-[11px] text-muted mt-1">{new Date(n.created_at).toLocaleString()}</p>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Add investigation note…"
          className="flex-1 text-sm rounded-lg border border-border-subtle bg-card-elevated px-3 py-2 text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent/50"
        />
        <button
          type="submit"
          disabled={!note.trim() || noteMutation.isPending}
          className="px-3 py-2 text-xs font-medium rounded-lg bg-accent text-white hover:bg-accent/90 disabled:opacity-50 transition-colors"
        >
          {noteMutation.isPending ? "Adding…" : "Add"}
        </button>
      </form>
    </div>
  );
}
