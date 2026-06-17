"use client";

import { TIME_PRESETS, useTimeRange } from "@/lib/timeRange";

export default function TimeRangeBar() {
  const { range, setPreset, setFrom, setTo } = useTimeRange();

  return (
    <div className="mb-6 p-3 bg-[var(--card)] border border-[var(--border)] rounded-lg flex flex-wrap gap-3 items-end">
      <div>
        <label className="text-xs text-gray-500 block mb-1">Time Range</label>
        <select
          value={range.preset}
          onChange={(e) => setPreset(e.target.value as typeof range.preset)}
          className="px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm"
        >
          {TIME_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>{p.label}</option>
          ))}
        </select>
      </div>
      {range.preset === "custom" && (
        <>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Start</label>
            <input type="datetime-local" value={range.from} onChange={(e) => setFrom(e.target.value)}
              className="px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">End</label>
            <input type="datetime-local" value={range.to} onChange={(e) => setTo(e.target.value)}
              className="px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm" />
          </div>
        </>
      )}
    </div>
  );
}
