"use client";

import { useState, useCallback } from "react";
import { useToast } from "@/components/ui/Toast";
import { useIncidentCreateMutation } from "@/lib/hooks/useIncidents";
import { INCIDENT_SEVERITIES } from "@/lib/types/incident";
import type { IncidentSeverity } from "@/lib/types/incident";
import { Button } from "@/components/design-system/Button";

interface Props {
  onCreated?: () => void;
}

export function IncidentCreateForm({ onCreated }: Props) {
  const { toast } = useToast();
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [severity, setSeverity] = useState<IncidentSeverity>("medium");

  const createMutation = useIncidentCreateMutation({
    onSuccess: () => {
      setTitle("");
      setDesc("");
      setSeverity("medium");
      toast("success", "Incident created");
      onCreated?.();
    },
    onError: (e) => toast("error", "Failed to create incident", e.message),
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim()) return;
      createMutation.mutate({ title: title.trim(), description: desc.trim() || undefined, severity });
    },
    [title, desc, severity, createMutation],
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-3 flex-wrap items-end">
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Incident title"
          className="flex-1 min-w-[200px] text-sm rounded-lg border border-border-subtle bg-card-elevated px-3 py-2 text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent/50"
          disabled={createMutation.isPending}
        />
        <input
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="Description (optional)"
          className="flex-1 min-w-[200px] text-sm rounded-lg border border-border-subtle bg-card-elevated px-3 py-2 text-foreground placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent/50"
          disabled={createMutation.isPending}
        />
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value as IncidentSeverity)}
          className="text-sm rounded-lg border border-border-subtle bg-card-elevated px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-accent/50"
          disabled={createMutation.isPending}
        >
          {INCIDENT_SEVERITIES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
        <Button type="submit" loading={createMutation.isPending}>
          Create Incident
        </Button>
      </div>
    </form>
  );
}
