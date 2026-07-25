"use client";

import { api } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

interface Props {
  resource: "events" | "alerts" | "hosts" | "audit";
  query: string;
}

export default function ExportMenu({ resource, query }: Props) {
  const { toast } = useToast();

  async function download(format: "csv" | "json" | "pdf") {
    try {
      const sep = query.includes("?") ? "&" : "?";
      const url = `/api/v1/${resource}/export${query}${sep}format=${format}`;
      const res = await api<Response>(url, { method: "GET" }, false);
      const blob = await res.blob();
      const a = document.createElement("a");
      const objectUrl = URL.createObjectURL(blob);
      a.href = objectUrl;
      a.download = `${resource}.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 100);
    } catch (err) {
      toast("error", "Export failed", err instanceof Error ? err.message : "Export failed");
    }
  }

  return (
    <div className="flex gap-2">
      {(["csv", "json", "pdf"] as const).map((f) => (
        <button key={f} type="button" onClick={() => download(f)} className="btn-ghost text-xs uppercase">{f}</button>
      ))}
    </div>
  );
}
