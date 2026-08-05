"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  host_id: string | null;
  created_at: string;
}

export interface IncidentDetail extends Incident {
  notes: { id: string; content: string; user_id: string; created_at: string }[];
  alert_ids: string[];
}

export function useIncidents() {
  return useQuery({
    queryKey: ["incidents"],
    queryFn: () => api<Incident[]>(API.INCIDENTS.LIST),
    staleTime: 30_000,
  });
}

export function useIncidentDetail(id: string | null) {
  return useQuery({
    queryKey: ["incidents", id],
    queryFn: () => api<IncidentDetail>(API.INCIDENTS.DETAIL(id!)),
    enabled: !!id,
    staleTime: 15_000,
  });
}

export function useIncidentCreateMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; description?: string; severity?: string; host_id?: string }) =>
      api(API.INCIDENTS.CREATE, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useIncidentStatusMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`${API.INCIDENTS.STATUS(id)}?status=${status}`, { method: "PATCH" }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["incidents", variables.id] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useIncidentAddNoteMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      api(API.INCIDENTS.NOTES(id), { method: "POST", body: JSON.stringify({ content }) }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["incidents", variables.id] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}
