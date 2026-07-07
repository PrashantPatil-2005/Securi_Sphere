"use client";

import { cn } from "@/lib/utils/cn";
import type { Scenario } from "@/lib/types/simulation";

const DIFFICULTY_STYLES: Record<string, string> = {
  beginner: "bg-success/10 text-success border-success/30",
  intermediate: "bg-warning/10 text-warning border-warning/30",
  advanced: "bg-danger/10 text-danger border-danger/30",
};

interface Props {
  scenario: Scenario;
  selected: boolean;
  onSelect: () => void;
}

export function ScenarioCard({ scenario, selected, onSelect }: Props) {
  const mitreIds = Array.from(
    new Set(
      scenario.steps
        .map((s) => s.mitre?.technique_id)
        .filter((id): id is string => !!id),
    ),
  );

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full text-left p-4 rounded-lg border transition-colors",
        selected
          ? "border-accent bg-accent/10 ring-1 ring-accent/30"
          : "border-border-subtle hover:bg-[var(--sidebar-hover)]",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium">{scenario.name}</span>
        <span
          className={cn(
            "text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border shrink-0",
            DIFFICULTY_STYLES[scenario.difficulty] ?? "bg-muted/10 text-muted border-border-subtle",
          )}
        >
          {scenario.difficulty}
        </span>
      </div>
      <p className="text-sm text-muted mt-1.5 line-clamp-2">{scenario.summary}</p>
      <div className="flex flex-wrap gap-2 mt-3 text-xs text-muted">
        <span>{scenario.event_count} events</span>
        <span>·</span>
        <span>{scenario.duration_seconds}s duration</span>
      </div>
      {mitreIds.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {mitreIds.slice(0, 4).map((id) => (
            <span
              key={id}
              className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20"
            >
              {id}
            </span>
          ))}
          {mitreIds.length > 4 && (
            <span className="text-[10px] text-muted">+{mitreIds.length - 4}</span>
          )}
        </div>
      )}
    </button>
  );
}
