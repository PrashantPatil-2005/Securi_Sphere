"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import { parsePaginatedList } from "@/lib/parseList";

export interface Host {
  id: string;
  name: string;
  hostname: string | null;
  ip_address: string | null;
  os_info: string | null;
  status: string;
  health_status: string;
  last_seen: string | null;
  created_at: string;
}

export function useHosts() {
  const { queryParams } = useTimeRange();
  return useQuery({
    queryKey: ["hosts", queryParams],
    queryFn: async () => {
      const r = await api<{ items?: Host[]; total?: number } | Host[]>(`${API.HOSTS.LIST}${buildQuery({}, queryParams)}`);
      return parsePaginatedList(r);
    },
    staleTime: 30_000,
  });
}

export function useHostDetail(id: string | null) {
  return useQuery({
    queryKey: ["hosts", id],
    queryFn: () => api<Host>(API.HOSTS.DETAIL(id!)),
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useHostRisk(id: string | null) {
  return useQuery({
    queryKey: ["hosts", "risk", id],
    queryFn: () =>
      api<{
        host_id: string;
        host_name: string;
        score: number;
        health_score: number;
        factors: Record<string, number>;
        factor_breakdown: { name: string; value: number; weight: number }[];
        history: { risk_score: number; health_score: number; recorded_at: string }[];
      }>(API.HOSTS.RISK(id!)),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useHostCreateMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; hostname?: string; ip_address?: string; os_info?: string }) =>
      api(API.HOSTS.CREATE, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hosts"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useHostDeleteMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(API.HOSTS.DETAIL(id), { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hosts"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}
