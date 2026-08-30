"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import type {
  EventSummary,
  EventListResponse,
  EventTypeCount,
  EventFilters,
} from "@/lib/types/event";

/** Normalize paginated or array response. */
function normalizeList(
  r: EventListResponse | EventSummary[] | null | undefined,
): { items: EventSummary[]; total: number; next_cursor: string | null; has_more: boolean } {
  if (Array.isArray(r)) {
    return { items: r, total: r.length, next_cursor: null, has_more: false };
  }
  return {
    items: r?.items ?? [],
    total: r?.total ?? 0,
    next_cursor: r?.next_cursor ?? null,
    has_more: r?.has_more ?? false,
  };
}

interface UseEventListParams {
  page: number;
  pageSize: number;
  sort: string;
  filters: EventFilters;
}

export function useEventList(params: UseEventListParams) {
  const { queryParams } = useTimeRange();
  const { page, pageSize, sort, filters } = params;

  return useQuery({
    queryKey: ["events", queryParams, page, pageSize, sort, filters],
    queryFn: async () => {
      const q = buildQuery(
        { page, page_size: pageSize, sort, ...filters },
        queryParams,
      );
      const r = await api<EventListResponse | EventSummary[]>(`${API.EVENTS.LIST}${q}`);
      return normalizeList(r);
    },
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });
}

/** Cursor-based event list (for keyset pagination). */
export function useEventCursorList(params: {
  pageSize: number;
  sort: string;
  filters: EventFilters;
}) {
  const { queryParams } = useTimeRange();
  const { pageSize, sort, filters } = params;
  const [page, setPage] = useState(1);
  const [cursors, setCursors] = useState<(string | null)[]>([null]);

  const resetKey = useMemo(
    () => JSON.stringify({ queryParams, pageSize, sort, filters }),
    [queryParams, pageSize, sort, filters],
  );

  useEffect(() => {
    setPage(1);
    setCursors([null]);
  }, [resetKey]);

  const activeCursor = cursors[page - 1] ?? null;

  const query = useQuery({
    queryKey: ["events", queryParams, page, pageSize, sort, filters, activeCursor],
    queryFn: async () => {
      const paging = activeCursor ? { cursor: activeCursor } : { page: 1 };
      const q = buildQuery(
        { page_size: pageSize, sort, ...filters, ...paging },
        queryParams,
      );
      const r = await api<EventListResponse | EventSummary[]>(`${API.EVENTS.LIST}${q}`);
      return normalizeList(r);
    },
    placeholderData: (prev) => prev,
    staleTime: 30_000,
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

/** Fetch event type aggregations for filter dropdown. */
export function useEventTypes() {
  return useQuery({
    queryKey: ["events", "types"],
    queryFn: () => api<EventTypeCount[]>(API.EVENTS.TYPES),
    staleTime: 5 * 60_000,
  });
}
