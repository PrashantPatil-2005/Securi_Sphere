"use client";

import { memo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useWsConnected } from "@/lib/websocket";
import { LoadingState } from "@/components/design-system/LoadingState";

interface SystemHealth {
  status: string;
  database: string;
  redis: string;
  environment: string;
  search_backend: string;
  job_queue_running: boolean;
  job_queue_pending: number;
  redis_configured: boolean;
}

interface HealthItemProps {
  label: string;
  status: "ok" | "degraded" | "error" | "unknown";
}

const statusDotColor: Record<string, string> = {
  ok: "bg-success",
  degraded: "bg-warning",
  error: "bg-danger",
  unknown: "bg-muted",
};

function StatusDot({ status }: { status: string }) {
  const color = statusDotColor[status] || "bg-muted";

  return (
    <span className="relative flex h-2 w-2">
      <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-40 ${color}`} />
      <span className={`relative inline-flex rounded-full h-2 w-2 ${color}`} />
    </span>
  );
}

function HealthItem({ label, status }: HealthItemProps) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-xs text-muted">{label}</span>
      <div className="flex items-center gap-1.5">
        <StatusDot status={status} />
        <span className="text-[11px] font-medium capitalize text-foreground">{status}</span>
      </div>
    </div>
  );
}

export const SystemHealthPanel = memo(function SystemHealthPanel() {
  const wsConnected = useWsConnected();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["system-health"],
    queryFn: () => api<SystemHealth>("/api/v1/system/health"),
    staleTime: 60_000,
    retry: 1,
  });

  if (isLoading) {
    return <LoadingState variant="inline" text="Checking system\u2026" />;
  }

  if (isError || !data) {
    return (
      <div className="space-y-1">
        <HealthItem label="API" status="unknown" />
        <HealthItem label="WebSocket" status={wsConnected ? "ok" : "error"} />
        <HealthItem label="Database" status="unknown" />
        <HealthItem label="Redis" status="unknown" />
        <HealthItem label="Search" status="unknown" />
      </div>
    );
  }

  const dbStatus = data.database === "connected" ? "ok" : data.database === "degraded" ? "degraded" : "error";
  const redisStatus = !data.redis_configured
    ? "unknown"
    : data.redis === "connected"
      ? "ok"
      : "degraded";
  const searchStatus = data.search_backend === "opensearch" ? "ok" : "ok";
  const queueStatus = data.job_queue_running ? "ok" : "degraded";

  return (
    <div className="space-y-0.5">
      <HealthItem label="API" status="ok" />
      <HealthItem label="WebSocket" status={wsConnected ? "ok" : "error"} />
      <HealthItem label="Database" status={dbStatus} />
      <HealthItem label="Redis" status={redisStatus} />
      <HealthItem label="Search" status={searchStatus} />
      <HealthItem label="Job Queue" status={queueStatus} />
    </div>
  );
});
