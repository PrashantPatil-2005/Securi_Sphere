"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import type {
  IncidentSummary,
  IncidentDetail,
  IncidentCreatePayload,
} from "@/lib/types/incident";

export function useIncidentList(params?: { status?: string }) {
  return useQuery({
    queryKey: ["incidents", params],
    queryFn: () => {
      const qs = params?.status ? `?status=${params.status}` : "";
      return api<IncidentSummary[]>(`${API.INCIDENTS.LIST}${qs}`);
    },
    staleTime: 30_000,
  });
}

export function useIncidentDetail(id: string | null) {
  return useQuery({
    queryKey: ["incidents", "detail", id],
    queryFn: () => api<IncidentDetail>(API.INCIDENTS.DETAIL(id!)),
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useIncidentCreateMutation(options?: {
  onSuccess?: (data: IncidentSummary) => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: IncidentCreatePayload) =>
      api<IncidentSummary>(API.INCIDENTS.CREATE, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      options?.onSuccess?.(data);
    },
    onError: options?.onError,
  });
}

export function useIncidentStatusMutation(options?: {
  onSuccess?: () => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`${API.INCIDENTS.STATUS(id)}?status=${status}`, { method: "PATCH" }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ["incidents"] });
      const previous = queryClient.getQueriesData({ queryKey: ["incidents"] });
      queryClient.setQueriesData({ queryKey: ["incidents"] }, (old: unknown) => {
        if (!old) return old;
        if (Array.isArray(old)) {
          return (old as { id: string; status: string }[]).map((i) =>
            i.id === id ? { ...i, status } : i,
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
    onSettled: (_data, _err, variables) => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["incidents", "detail", variables.id] });
      options?.onSuccess?.();
    },
  });
}

export function useIncidentAddNoteMutation(options?: {
  onSuccess?: () => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      api(API.INCIDENTS.NOTES(id), {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["incidents", "detail", variables.id] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}
