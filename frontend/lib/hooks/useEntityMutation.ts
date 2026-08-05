"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface UseEntityMutationOptions<TBody, TResponse = unknown> {
  endpoint: string | ((body: TBody) => string);
  method: "POST" | "PATCH" | "PUT" | "DELETE";
  invalidates?: unknown[][];
  onSuccess?: (data: TResponse) => void;
  onError?: (error: Error) => void;
}

export function useEntityMutation<TBody, TResponse = unknown>(
  options: UseEntityMutationOptions<TBody, TResponse>,
) {
  const queryClient = useQueryClient();
  const { endpoint, method, invalidates = [], onSuccess, onError } = options;

  return useMutation({
    mutationFn: async (body: TBody) => {
      const url = typeof endpoint === "function" ? endpoint(body) : endpoint;
      return api<TResponse>(url, {
        method,
        body: method !== "DELETE" ? JSON.stringify(body) : undefined,
      });
    },
    onSuccess: (data) => {
      for (const queryKey of invalidates) {
        queryClient.invalidateQueries({ queryKey });
      }
      onSuccess?.(data);
    },
    onError,
  });
}

/** Convenience hook for status-update mutations (PATCH /{entity}/{id}/status). */
export function useStatusMutation(
  entity: string,
  options?: { onSuccess?: () => void; onError?: (error: Error) => void },
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/api/v1/${entity}/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [entity] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}
