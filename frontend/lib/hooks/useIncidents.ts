"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import { parsePaginatedList } from "@/lib/parseList";
import type {
  IncidentSummary,
  IncidentResponse,
  IncidentDetail,
  IncidentCreatePayload,
} from "@/lib/types/incident";

/**
 * Full incident list (backend has no filter params beyond status), parsed into
 * a stable `{ items, total }` envelope so callers can filter/sort/page client-side.
 */
export function useIncidentList() {
  return useQuery({
    queryKey: ["incidents", "list"],
    queryFn: async () => {
      const r = await api<IncidentResponse[] | { items?: IncidentResponse[]; total?: number }>(
        `${API.INCIDENTS.LIST}?page_size=500`,
      );
      return parsePaginatedList(r);
    },
    placeholderData: (prev) => prev,
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
        const envelope = old as { items?: { id: string; status: string }[] };
        if (Array.isArray(envelope.items)) {
          return {
            ...envelope,
            items: envelope.items.map((i) => (i.id === id ? { ...i, status } : i)),
          };
        }
        const detail = old as { id?: string; status?: string };
        if (detail.id === id) return { ...old, status };
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

/** Bulk status update — backend has no bulk endpoint, so fan out per incident. */
export function useIncidentBulkStatusMutation(options?: {
  onSuccess?: (result: { updated: number; failed: number }) => void;
  onError?: (e: Error) => void;
}) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ ids, status }: { ids: string[]; status: string }) => {
      const results = await Promise.allSettled(
        ids.map((id) =>
          api(`${API.INCIDENTS.STATUS(id)}?status=${status}`, { method: "PATCH" }),
        ),
      );
      const failed = results.filter((r) => r.status === "rejected").length;
      if (failed === ids.length) throw new Error("Failed to update any incident");
      return { updated: ids.length - failed, failed };
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      options?.onSuccess?.(result);
    },
    onError: (e: Error) => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      options?.onError?.(e);
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
