"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { parsePaginatedList } from "@/lib/parseList";
import { useTimeRange } from "@/lib/timeRange";
import { useSimulationQueryParams } from "@/lib/simulation-session";
import type {
  Alert,
  AlertListResponse,
  InvestigationData,
  AlertAiSummary,
} from "@/lib/types/alert";

export function useAlertList(params: {
  page: number;
  pageSize: number;
  sort: string;
  filters: Record<string, string | number | boolean | undefined | null>;
}) {
  const { queryParams } = useTimeRange();
  const simParams = useSimulationQueryParams();
  const { page, pageSize, sort, filters } = params;

  return useQuery({
    queryKey: ["alerts", queryParams, simParams, page, pageSize, sort, filters],
    queryFn: async () => {
      const q = buildQuery(
        { page, page_size: pageSize, sort, ...simParams, ...filters },
        queryParams,
      );
      const r = await api<AlertListResponse | { items?: Alert[]; total?: number }>(
        `/api/v1/alerts${q}`,
      );
      return parsePaginatedList(r);
    },
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });
}

export function useAlertDetail(id: string | null) {
  return useQuery({
    queryKey: ["alerts", "detail", id],
    queryFn: () => api<Alert>(`/api/v1/alerts/${id}`),
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useAlertInvestigation(id: string | null) {
  return useQuery({
    queryKey: ["alerts", "investigation", id],
    queryFn: () => api<InvestigationData>(`/api/v1/alerts/${id}/investigation`),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useAlertAiSummary(id: string | null) {
  return useQuery({
    queryKey: ["alerts", "ai-summary", id],
    queryFn: () => api<AlertAiSummary>(`/api/v1/alerts/${id}/ai-summary`),
    enabled: !!id,
    staleTime: 120_000,
  });
}

export function useAlertStatusMutation(onSuccess?: () => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/alerts/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ["alerts"] });
      const previous = queryClient.getQueriesData({ queryKey: ["alerts"] });
      queryClient.setQueriesData({ queryKey: ["alerts"] }, (old: unknown) => {
        if (!old || typeof old !== "object") return old;
        const data = old as { items?: { id: string; status: string }[]; total?: number };
        if (Array.isArray(data.items)) {
          return {
            ...data,
            items: data.items.map((a) =>
              a.id === id ? { ...a, status } : a,
            ),
          };
        }
        if (Array.isArray(old)) {
          return (old as { id: string; status: string }[]).map((a) =>
            a.id === id ? { ...a, status } : a,
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
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      onSuccess?.();
    },
  });
}

export function useAlertBulkMutation(onSuccess?: () => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      alert_ids: string[];
      status?: string;
      assigned_to?: string;
    }) =>
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

export function useAlertFeedbackMutation(alertId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { label: "false_positive" | "true_positive"; note?: string }) =>
      api(`/api/v1/alerts/${alertId}/feedback`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({
        queryKey: ["alerts", "investigation", alertId],
      });
    },
  });
}
