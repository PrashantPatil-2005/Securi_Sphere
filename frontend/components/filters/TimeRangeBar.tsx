"use client";

import { memo } from "react";
import { TIME_PRESETS, useTimeRange } from "@/lib/timeRange";
import { cn } from "@/lib/utils/cn";

interface TimeRangeBarProps {
  variant?: "panel" | "inline";
  className?: string;
}

function TimeRangeBar({ variant = "inline", className }: TimeRangeBarProps) {
  const { range, setPreset, setFrom, setTo } = useTimeRange();

  const controls = (
    <div className={cn("flex flex-wrap gap-3 items-end", variant === "panel" && "py-3", className)}>
      <div>
        <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">Time range</label>
        <select
          value={range.preset}
          onChange={(e) => setPreset(e.target.value as typeof range.preset)}
          className="input-siem min-w-[160px]"
        >
          {TIME_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>
      {range.preset === "custom" && (
        <>
          <div>
            <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">Start</label>
            <input type="datetime-local" value={range.from} onChange={(e) => setFrom(e.target.value)} className="input-siem" />
          </div>
          <div>
            <label className="text-[11px] uppercase tracking-wide text-[var(--muted)] block mb-1">End</label>
            <input type="datetime-local" value={range.to} onChange={(e) => setTo(e.target.value)} className="input-siem" />
          </div>
        </>
      )}
    </div>
  );

  if (variant === "panel") {
    return <div className="panel mb-5"><div className="panel-body">{controls}</div></div>;
  }

  return <div className="mb-4">{controls}</div>;
}

export default memo(TimeRangeBar);
