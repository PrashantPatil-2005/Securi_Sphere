import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { UebaAnomaly, UebaSummary, UebaScanResponse } from "@/lib/types/ueba";

export function useUebaSummary() {
  return useQuery({
    queryKey: ["ueba", "summary"],
    queryFn: () => api<UebaSummary>("/api/v1/ueba/summary"),
    staleTime: 60_000,
  });
}

export function useUebaAnomalies(params: {
  status?: string;
  severity?: string;
  entityType?: string;
  limit?: number;
}) {
  const { status, severity, entityType, limit = 50 } = params;
  const qParts: string[] = [`limit=${limit}`];
  if (status) qParts.push(`status=${status}`);
  if (severity) qParts.push(`severity=${severity}`);
  if (entityType) qParts.push(`entity_type=${entityType}`);
  const q = qParts.length ? `?${qParts.join("&")}` : "";

  return useQuery({
    queryKey: ["ueba", "anomalies", status, severity, entityType, limit],
    queryFn: () => api<UebaAnomaly[]>(`/api/v1/ueba/anomalies${q}`),
    staleTime: 30_000,
  });
}

export function useUebaScanMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api<UebaScanResponse>("/api/v1/ueba/scan", { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ueba"] });
    },
  });
}

export function useUebaUpdateMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: "dismissed" | "resolved" }) =>
      api<UebaAnomaly>(`/api/v1/ueba/anomalies/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ueba"] });
    },
  });
}
