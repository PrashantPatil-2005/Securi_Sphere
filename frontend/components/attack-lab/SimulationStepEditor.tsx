"use client";

import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import type { CustomStepDraft, EventTypeOption } from "@/lib/types/simulation";

const SEVERITIES = ["info", "low", "medium", "high", "critical"];

interface Props {
  step: CustomStepDraft;
  index: number;
  total: number;
  eventTypes: EventTypeOption[];
  onChange: (step: CustomStepDraft) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

export function SimulationStepEditor({
  step,
  index,
  total,
  eventTypes,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}: Props) {
  return (
    <div className="flex flex-wrap items-end gap-2 p-3 rounded-lg border border-border-subtle bg-[var(--sidebar-hover)]/30">
      <span className="text-xs text-muted w-6 shrink-0 pb-2 tabular-nums">{index + 1}</span>
      <label className="flex-1 min-w-[140px]">
        <span className="text-xs text-muted block mb-1">Event type</span>
        <select
          value={step.event_type}
          onChange={(e) => onChange({ ...step, event_type: e.target.value })}
          className="input-siem w-full text-sm"
        >
          {eventTypes.map((t) => (
            <option key={t.event_type} value={t.event_type}>
              {t.event_type}
            </option>
          ))}
        </select>
      </label>
      <label className="w-24">
        <span className="text-xs text-muted block mb-1">Offset (s)</span>
        <input
          type="number"
          min={0}
          max={3600}
          value={step.offset_seconds}
          onChange={(e) => onChange({ ...step, offset_seconds: Number(e.target.value) || 0 })}
          className="input-siem w-full text-sm"
        />
      </label>
      <label className="w-28">
        <span className="text-xs text-muted block mb-1">Severity</span>
        <select
          value={step.severity}
          onChange={(e) => onChange({ ...step, severity: e.target.value })}
          className="input-siem w-full text-sm"
        >
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>
      <div className="flex gap-1 pb-0.5">
        <button
          type="button"
          className="btn-ghost p-1.5"
          disabled={index === 0}
          onClick={onMoveUp}
          aria-label="Move step up"
        >
          <ChevronUp className="w-4 h-4" />
        </button>
        <button
          type="button"
          className="btn-ghost p-1.5"
          disabled={index === total - 1}
          onClick={onMoveDown}
          aria-label="Move step down"
        >
          <ChevronDown className="w-4 h-4" />
        </button>
        <button
          type="button"
          className="btn-ghost p-1.5 text-danger"
          disabled={total <= 1}
          onClick={onRemove}
          aria-label="Remove step"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
