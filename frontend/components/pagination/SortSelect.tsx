"use client";

import { SORT_OPTIONS } from "@/lib/buildQuery";

export default function SortSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className="px-3 py-1.5 bg-black/30 border border-[var(--border)] rounded text-sm">
      {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}
