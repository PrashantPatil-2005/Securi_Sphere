"use client";

import { API_URL } from "@/lib/api";

interface Props {
  resource: "events" | "alerts" | "hosts";
  query: string;
}

export default function ExportMenu({ resource, query }: Props) {
  async function download(format: "csv" | "json" | "pdf") {
    const token = localStorage.getItem("access_token");
    const sep = query.includes("?") ? "&" : "?";
    const url = `${API_URL}/api/v1/${resource}/export${query}${sep}format=${format}`;
    const res = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!res.ok) return;
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${resource}.${format}`;
    a.click();
  }

  return (
    <div className="flex gap-2">
      {(["csv", "json", "pdf"] as const).map((f) => (
        <button key={f} onClick={() => download(f)} className="text-xs px-3 py-1.5 border border-[var(--border)] rounded hover:bg-white/5 uppercase">{f}</button>
      ))}
    </div>
  );
}
