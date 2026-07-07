"use client";

import { Shield, ShieldAlert } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils/cn";

interface AuditIntegrity {
  valid: boolean;
  immutable_enabled: boolean;
  entries_checked: number;
  chain_head_hash: string | null;
  latest_chain_seq: number | null;
  failure: {
    chain_seq: number;
    reason: string;
    expected?: string | null;
    actual?: string | null;
  } | null;
}

export function AuditIntegrityPanel() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit-integrity"],
    queryFn: () => api<AuditIntegrity>("/api/v1/audit/integrity"),
    staleTime: 60_000,
    refetchInterval: 120_000,
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border-subtle bg-surface/50 px-4 py-3 text-sm text-muted">
        Verifying audit chain…
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg border border-severity-high/30 bg-severity-high/5 px-4 py-3 text-sm text-severity-high">
        Unable to verify audit chain integrity.
      </div>
    );
  }

  const Icon = data.valid ? Shield : ShieldAlert;

  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3 text-sm flex items-start gap-3",
        data.valid
          ? "border-severity-low/30 bg-severity-low/5"
          : "border-severity-high/30 bg-severity-high/5",
      )}
    >
      <Icon className={cn("w-5 h-5 shrink-0 mt-0.5", data.valid ? "text-severity-low" : "text-severity-high")} />
      <div className="min-w-0">
        <p className="font-medium text-foreground">
          {data.valid ? "Audit chain verified" : "Audit chain integrity failure"}
        </p>
        <p className="text-muted mt-0.5">
          {data.immutable_enabled ? "Append-only store with hash chain" : "Hash chain enabled"}
          {" · "}
          {data.entries_checked.toLocaleString()} entries checked
          {data.latest_chain_seq != null ? ` · seq ${data.latest_chain_seq}` : ""}
        </p>
        {data.valid && data.chain_head_hash && (
          <p className="text-xs text-muted font-mono mt-1 truncate" title={data.chain_head_hash}>
            head {data.chain_head_hash.slice(0, 16)}…
          </p>
        )}
        {!data.valid && data.failure && (
          <p className="text-xs text-severity-high mt-1">
            seq {data.failure.chain_seq}: {data.failure.reason}
          </p>
        )}
      </div>
    </div>
  );
}
