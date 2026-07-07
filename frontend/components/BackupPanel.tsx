"use client";

import { Database, Loader2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";
import { useToast } from "@/components/ui/Toast";

interface BackupItem {
  filename: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
  trigger: string;
  status: string;
}

interface BackupList {
  items: BackupItem[];
  config: {
    enabled: boolean;
    directory: string;
    retention_days: number;
    schedule_hour: number;
    pg_dump_available: boolean;
  };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function BackupPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["backups"],
    queryFn: () => api<BackupList>("/api/v1/backups"),
    staleTime: 30_000,
  });

  const runBackup = useMutation({
    mutationFn: () => api<BackupItem>("/api/v1/backups/run", { method: "POST" }),
    onSuccess: (record) => {
      toast("success", "Backup complete", record.filename);
      queryClient.invalidateQueries({ queryKey: ["backups"] });
    },
    onError: (err: Error) => {
      toast("error", "Backup failed", err.message);
    },
  });

  return (
    <Panel title="Database backups" subtitle="Scheduled pg_dump with retention">
      {isLoading && <p className="text-sm text-muted">Loading backups…</p>}
      {isError && <p className="text-sm text-severity-high">Unable to load backup status.</p>}
      {data && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-muted space-y-1">
              <p>
                {data.config.enabled ? "Enabled" : "Disabled"}
                {" · "}
                Daily at {String(data.config.schedule_hour).padStart(2, "0")}:00 UTC
                {" · "}
                Retain {data.config.retention_days} days
              </p>
              <p className="font-mono text-xs">{data.config.directory}</p>
              {!data.config.pg_dump_available && (
                <p className="text-warning text-xs">pg_dump not available on API host — use scripts/backup-postgres.sh via cron</p>
              )}
            </div>
            <button
              type="button"
              className="btn-primary text-sm"
              disabled={!data.config.enabled || runBackup.isPending}
              onClick={() => runBackup.mutate()}
            >
              {runBackup.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running…
                </span>
              ) : (
                "Run backup now"
              )}
            </button>
          </div>
          {data.items.length === 0 ? (
            <p className="text-sm text-muted flex items-center gap-2">
              <Database className="w-4 h-4 opacity-60" />
              No backups yet — wait for the schedule or run one manually.
            </p>
          ) : (
            <ul className="divide-y divide-border-subtle/50 text-sm">
              {data.items.slice(0, 5).map((item) => (
                <li key={item.filename} className="py-2 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-mono truncate">{item.filename}</p>
                    <p className="text-xs text-muted">
                      {new Date(item.created_at).toLocaleString()} · {item.trigger} · {item.status}
                    </p>
                  </div>
                  <span className="text-muted shrink-0">{formatBytes(item.size_bytes)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Panel>
  );
}
