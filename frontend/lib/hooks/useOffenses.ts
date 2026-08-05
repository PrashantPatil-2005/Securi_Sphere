"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";

export interface Offense {
  id: string;
  offense_number: number;
  host_id?: string;
  host_name: string;
  title: string;
  risk_level: string;
  status: string;
  event_count: number;
  created_at: string;
}

export interface OffenseDetail extends Offense {
  incident_id?: string | null;
  events: { event_type: string; description: string | null; timestamp: string; severity: string }[];
  alerts: { id: string; title: string; severity: string; status: string; created_at: string }[];
  timeline?: { ts: string; type: string; detail: string }[];
  related_hosts?: string[];
  related_users?: string[];
}

export function useOffenses() {
  const { queryParams } = useTimeRange();
  return useQuery({
    queryKey: ["offenses", queryParams],
    queryFn: () => api<{ items: Offense[] }>(`${API.OFFENSES.LIST}${buildQuery({}, queryParams)}`),
    staleTime: 30_000,
  });
}

export function useOffenseDetail(id: string | null) {
  return useQuery({
    queryKey: ["offenses", id],
    queryFn: () => api<OffenseDetail>(API.OFFENSES.DETAIL(id!)),
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useOffenseAiBrief(id: string | null) {
  return useQuery({
    queryKey: ["offenses", "ai-brief", id],
    queryFn: () =>
      api<{ brief: string; key_findings: string[]; recommended_actions: string[] }>(
        API.OFFENSES.AI_BRIEF(id!),
      ),
    enabled: !!id,
    staleTime: 120_000,
  });
}

export function useOffenseStatusMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(API.OFFENSES.STATUS(id), { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useOffensePromoteMutation(options?: { onSuccess?: (data: { incident_id: string; created: boolean }) => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<{ incident_id: string; created: boolean; linked_alert_count: number }>(
        API.OFFENSES.PROMOTE(id),
        { method: "POST" },
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["incidents", "count"] });
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });
}
