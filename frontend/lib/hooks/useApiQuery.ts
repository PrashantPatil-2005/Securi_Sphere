"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import { useTimeRange } from "@/lib/timeRange";

export interface MaintenanceWindow {
  id: string;
  host_id: string;
  host_name: string;
  reason: string | null;
  starts_at: string;
  ends_at: string;
  active: boolean;
}

export function useMaintenanceWindows() {
  return useQuery({
    queryKey: ["maintenance-windows"],
    queryFn: () => api<MaintenanceWindow[]>("/api/v1/maintenance-windows"),
    staleTime: 30_000,
  });
}

export function useHostsList() {
  return useQuery({
    queryKey: ["hosts", "options"],
    queryFn: async () => {
      const r = await api<{ items?: { id: string; name: string }[] } | { id: string; name: string }[]>(
        "/api/v1/hosts?page_size=500",
      );
      return parsePaginatedList(r).items;
    },
    staleTime: 5 * 60_000,
  });
}

export function useSiemQuery<T>(path: string, extra: Record<string, string> = {}, enabled = true) {
  const { queryParams } = useTimeRange();
  return useQuery({
    queryKey: ["siem", path, queryParams, extra],
    queryFn: async () => {
      const q = buildQuery(extra, queryParams);
      return api<T>(`/api/v1/siem/${path}${q}`);
    },
    enabled,
    staleTime: 45_000,
    placeholderData: keepPreviousData,
  });
}
