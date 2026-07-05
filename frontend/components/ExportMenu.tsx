"use client";

import { API_URL } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

interface Props {
  resource: "events" | "alerts" | "hosts";
  query: string;
}

export default function ExportMenu({ resource, query }: Props) {
  const { toast } = useToast();

  async function download(format: "csv" | "json" | "pdf") {
    const sep = query.includes("?") ? "&" : "?";
    const url = `${API_URL}/api/v1/${resource}/export${query}${sep}format=${format}`;
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) {
      toast("error", "Export failed", res.status === 403 ? "Insufficient permissions" : `Server returned ${res.status}`);
      return;
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${resource}.${format}`;
    a.click();
  }

  return (
    <div className="flex gap-2">
      {(["csv", "json", "pdf"] as const).map((f) => (
        <button key={f} type="button" onClick={() => download(f)} className="btn-ghost text-xs uppercase">{f}</button>
      ))}
    </div>
  );
}
