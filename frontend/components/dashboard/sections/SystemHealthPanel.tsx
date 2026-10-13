"use client";

import { memo } from "react";
import { RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useWsConnected } from "@/lib/websocket";
import { LoadingState } from "@/components/design-system/LoadingState";
import type { ComponentHealthResponse, ComponentHealthState } from "@/lib/types/system";

/** Dashboard summary panel: per-component 4-state status from /system/health/components. */
export const SystemHealthPanel = memo(function SystemHealthPanel() {
  const wsConnected = useWsConnected();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["system", "health", "components"],
    queryFn: () => api<ComponentHealthResponse>("/api/v1/system/health/components"),
    staleTime: 30_000,
    retry: 1,
  });

  if (isLoading) {
    return <LoadingState variant="inline" text="Checking system\u2026" />;
  }

  if (isError || !data) {
    return (
      <div className="space-y-2">
        <p className="text-xs text-muted">Component health unavailable.</p>
        <p className="text-xs text-warning">WebSocket (local): {wsConnected ? "connected" : "disconnected"}</p>
        <button
          type="button"
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-[11px] text-muted hover:text-accent transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Retry component health
        </button>
      </div>
    );
  }

  const dotColor: Record<ComponentHealthState, string> = {
    healthy: "bg-success",
    degraded: "bg-warning",
    unavailable: "bg-danger",
    unknown: "bg-muted",
  };

  return (
    <div className="space-y-0.5">
      {data.components.map((c) => (
        <div key={c.id} className="flex items-center justify-between py-1.5">
          <span className="text-xs text-muted">{c.name}</span>
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-40 ${dotColor[c.status]}`}
              />
              <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColor[c.status]}`} />
            </span>
            <span className="text-[11px] font-medium capitalize text-foreground">{c.status}</span>
          </div>
        </div>
      ))}
    </div>
  );
});
