"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import type {
  HostSummary,
  HostListResponse,
  HostRiskDetail,
  HostFilters,
} from "@/lib/types/host";

export function useHostList(params: {
  page: number;
  pageSize: number;
  sort: string;
  filters: HostFilters;
}) {
  const { page, pageSize, sort, filters } = params;

  return useQuery({
    queryKey: ["hosts", page, pageSize, sort, filters],
    queryFn: async () => {
      const q = buildQuery(
        { page, page_size: pageSize, sort, ...filters },
        {},
      );
      const r = await api<HostListResponse | HostSummary[]>(`${API.HOSTS.LIST}${q}`);
      return parsePaginatedList(r);
    },
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });
}

export function useHostDetail(id: string | null) {
  return useQuery({
    queryKey: ["hosts", "detail", id],
    queryFn: () => api<HostSummary>(API.HOSTS.DETAIL(id!)),
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useHostRisk(id: string | null) {
  return useQuery({
    queryKey: ["hosts", "risk", id],
    queryFn: () => api<HostRiskDetail>(API.HOSTS.RISK(id!)),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useHostCreateMutation(options?: {
  onSuccess?: (data: any) => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string }) =>
      api<{ id: string }>(API.HOSTS.CREATE, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["hosts"] });
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });
}

export function useHostDeleteMutation(options?: {
  onSuccess?: () => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (hostId: string) =>
      api(API.HOSTS.DELETE(hostId), { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["hosts"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export interface EnrollmentTokenResponse {
  token: string;
  expires_at: string;
  install_command: string;
  host_id: string;
  host_name: string;
}

export function useEnrollmentTokenMutation(options?: {
  onSuccess?: (data: EnrollmentTokenResponse) => void;
  onError?: (e: Error) => void;
}) {
  return useMutation({
    mutationFn: (hostId: string) =>
      api<EnrollmentTokenResponse>(API.HOSTS.ENROLLMENT_TOKEN(hostId), {
        method: "POST",
      }),
    onSuccess: options?.onSuccess,
    onError: options?.onError,
  });
}

/** Fetch alerts for a specific host. */
export function useHostAlerts(hostId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["alerts", "host", hostId],
    queryFn: async () => {
      const r = await api<{
        items?: { id: string; title: string; severity: string; status: string; created_at: string }[];
        total?: number;
      }>(`${API.ALERTS.LIST}?host_id=${hostId}&page_size=10&sort=newest`);
      return parsePaginatedList(r);
    },
    enabled: enabled && !!hostId,
    staleTime: 30_000,
  });
}

/** Fetch events for a specific host. */
export function useHostEvents(hostId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["events", "host", hostId],
    queryFn: async () => {
      const r = await api<{
        items?: { id: string; event_type: string; severity: string; description: string | null; timestamp: string; source: string | null }[];
        total?: number;
      }>(`${API.EVENTS.LIST}?host_id=${hostId}&page_size=10&sort=newest`);
      return parsePaginatedList(r);
    },
    enabled: enabled && !!hostId,
    staleTime: 30_000,
  });
}

/** Fetch offenses for a specific host. */
export function useHostOffenses(hostId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["offenses", "host", hostId],
    queryFn: async () => {
      const r = await api<{
        items?: { id: string; offense_number: number; title: string; risk_level: string; status: string; created_at: string }[];
        total?: number;
      }>(`${API.OFFENSES.LIST}?host_id=${hostId}&page_size=10`);
      return parsePaginatedList(r);
    },
    enabled: enabled && !!hostId,
    staleTime: 30_000,
  });
}

/** Fetch metrics for a specific host (latest). */
export function useHostMetrics(hostId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["metrics", "host", hostId],
    queryFn: () =>
      api<{
        id: string;
        cpu_percent: number | null;
        memory_percent: number | null;
        disk_percent: number | null;
        network_in: number | null;
        network_out: number | null;
        uptime_seconds: number | null;
        recorded_at: string;
      }[]>(`/api/v1/metrics?host_id=${hostId!}&limit=1`),
    enabled: enabled && !!hostId,
    staleTime: 30_000,
  });
}
