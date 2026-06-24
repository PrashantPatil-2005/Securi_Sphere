"use client";

import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import { useTimeRange } from "@/lib/timeRange";

export function useTimeQueryKey(base: string, extra: Record<string, unknown> = {}) {
  const { queryParams } = useTimeRange();
  return [base, queryParams, extra] as const;
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

interface PaginatedParams {
  endpoint: string;
  queryKey: string;
  page: number;
  pageSize: number;
  sort: string;
  filters: Record<string, string | number | boolean | undefined | null>;
  /** When false, omit global time-range params (e.g. host inventory). */
  includeTimeRange?: boolean;
}

export function usePaginatedResource<T>({
  endpoint,
  queryKey,
  page,
  pageSize,
  sort,
  filters,
  includeTimeRange = true,
}: PaginatedParams) {
  const { queryParams } = useTimeRange();
  const timeParams = includeTimeRange ? queryParams : {};
  return useQuery({
    queryKey: [queryKey, timeParams, page, pageSize, sort, filters],
    queryFn: async () => {
      const q = buildQuery({ page, page_size: pageSize, sort, ...filters }, timeParams);
      const r = await api<{ items?: T[]; total?: number } | T[]>(`${endpoint}${q}`);
      return parsePaginatedList(r);
    },
    placeholderData: (prev) => prev,
    staleTime: includeTimeRange ? 0 : 15_000,
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
  });
}

export function useAlertStatusMutation(onSuccess?: () => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/alerts/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      onSuccess?.();
    },
  });
}
