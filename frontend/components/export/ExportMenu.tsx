"use client";

import { downloadAuthenticated } from "@/lib/download";
import { API } from "@/lib/api/endpoints";
import { useToast } from "@/components/ui/Toast";

const EXPORT_PATHS: Record<string, string> = {
  events: API.EVENTS.EXPORT,
  alerts: API.ALERTS.EXPORT,
  hosts: API.HOSTS.LIST + "/export",
  audit: API.AUDIT.LIST + "/export",
};

interface Props {
  resource: "events" | "alerts" | "hosts" | "audit";
  query: string;
}

export default function ExportMenu({ resource, query }: Props) {
  const { toast } = useToast();

  async function download(format: "csv" | "json" | "pdf") {
    try {
      const sep = query.includes("?") ? "&" : "?";
      const path = EXPORT_PATHS[resource] ?? `/api/v1/${resource}/export`;
      await downloadAuthenticated(`${path}${query}${sep}format=${format}`, `${resource}.${format}`);
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
