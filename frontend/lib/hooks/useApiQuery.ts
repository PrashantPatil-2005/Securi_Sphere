"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import { useTimeRange } from "@/lib/timeRange";

export function useTimeQueryKey(base: string, extra: Record<string, unknown> = {}) {
  const { queryParams } = useTimeRange();
  return [base, queryParams, extra] as const;
}

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

interface CursorPaginatedParams {
  endpoint: string;
  queryKey: string;
  pageSize: number;
  sort: string;
  filters: Record<string, string | number | boolean | undefined | null>;
  includeTimeRange?: boolean;
}

export function useCursorPaginatedResource<T>({
  endpoint,
  queryKey,
  pageSize,
  sort,
  filters,
  includeTimeRange = true,
}: CursorPaginatedParams) {
  const { queryParams } = useTimeRange();
  const timeParams = useMemo(
    () => (includeTimeRange ? queryParams : {}),
    [includeTimeRange, queryParams],
  );
  const [page, setPage] = useState(1);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);

  const resetKey = useMemo(
    () => JSON.stringify({ timeParams, pageSize, sort, filters }),
    [timeParams, pageSize, sort, filters],
  );

  useEffect(() => {
    setPage(1);
    setCursors([null]);
  }, [resetKey]);

  const activeCursor = cursors[page - 1] ?? null;

  const query = useQuery({
    queryKey: [queryKey, timeParams, page, pageSize, sort, filters, activeCursor],
    queryFn: async () => {
      const paging = activeCursor ? { cursor: activeCursor } : { page: 1 };
      const q = buildQuery({ page_size: pageSize, sort, ...filters, ...paging }, timeParams);
      const r = await api<{
        items?: T[];
        total?: number;
        next_cursor?: string | null;
        has_more?: boolean;
      } | T[]>(`${endpoint}${q}`);
      return parsePaginatedList(r);
    },
    placeholderData: (prev) => prev,
    staleTime: includeTimeRange ? 0 : 15_000,
  });

  const goNext = useCallback(() => {
    const next = query.data?.next_cursor;
    if (!next || !query.data?.has_more) return;
    setCursors((prev) => {
      const copy = [...prev];
      copy[page] = next;
      return copy;
    });
    setPage((p) => p + 1);
  }, [page, query.data]);

  const goPrev = useCallback(() => {
    setPage((p) => Math.max(1, p - 1));
  }, []);

  return {
    ...query,
    page,
    pageSize,
    goNext,
    goPrev,
    hasMore: query.data?.has_more ?? false,
    total: query.data?.total ?? 0,
    items: query.data?.items ?? [],
  };
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

export function useAlertBulkMutation(onSuccess?: () => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { alert_ids: string[]; status?: string; assigned_to?: string }) =>
      api<{ updated: number; not_found: string[] }>("/api/v1/alerts/bulk", {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      onSuccess?.();
    },
  });
}
