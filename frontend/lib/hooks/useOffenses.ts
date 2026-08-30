"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import type {
  OffenseDetail,
  OffenseAiBrief,
  OffenseListResponse,
  OffensePromoteResponse,
  OffenseFilters,
} from "@/lib/types/offense";

export function useOffenseList(params: {
  page: number;
  pageSize: number;
  filters: OffenseFilters;
}) {
  const { queryParams } = useTimeRange();
  const { page, pageSize, filters } = params;

  return useQuery({
    queryKey: ["offenses", queryParams, page, pageSize, filters],
    queryFn: async () => {
      const q = buildQuery(
        { page, page_size: pageSize, ...filters },
        queryParams,
      );
      const r = await api<OffenseListResponse>(`${API.OFFENSES.LIST}${q}`);
      return r;
    },
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });
}

export function useOffenseDetail(id: string | null) {
  return useQuery({
    queryKey: ["offenses", "detail", id],
    queryFn: () => api<OffenseDetail>(API.OFFENSES.DETAIL(id!)),
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useOffenseAiBrief(id: string | null) {
  return useQuery({
    queryKey: ["offenses", "ai-brief", id],
    queryFn: () => api<OffenseAiBrief>(API.OFFENSES.AI_BRIEF(id!)),
    enabled: !!id,
    staleTime: 120_000,
  });
}

export function useOffenseStatusMutation(options?: {
  onSuccess?: () => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(API.OFFENSES.STATUS(id), {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ["offenses"] });
      const previous = queryClient.getQueriesData({ queryKey: ["offenses"] });
      queryClient.setQueriesData({ queryKey: ["offenses"] }, (old: unknown) => {
        if (!old || typeof old !== "object") return old;
        const data = old as { items?: { id: string; status: string }[]; total?: number };
        if (Array.isArray(data.items)) {
          return {
            ...data,
            items: data.items.map((o) =>
              o.id === id ? { ...o, status } : o,
            ),
          };
        }
        if (Array.isArray(old)) {
          return (old as { id: string; status: string }[]).map((o) =>
            o.id === id ? { ...o, status } : o,
          );
        }
        return old;
      });
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        for (const [key, data] of context.previous) {
          queryClient.setQueryData(key, data);
        }
      }
      options?.onError?.(_err);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
      options?.onSuccess?.();
    },
  });
}

export function useOffensePromoteMutation(options?: {
  onSuccess?: (data: OffensePromoteResponse) => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api<OffensePromoteResponse>(API.OFFENSES.PROMOTE(id), { method: "POST" }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });
}
