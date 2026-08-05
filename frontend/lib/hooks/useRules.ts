"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";

export interface AlertRule {
  id: string;
  name: string;
  rule_type: string;
  threshold: number | null;
  window_minutes: number | null;
  severity: string;
  enabled: boolean;
  false_positive_count: number;
  true_positive_count: number;
}

export interface CorrelationRule {
  id: string;
  name: string;
  description: string | null;
  event_sequence: string[];
  window_minutes: number;
  min_occurrences: Record<string, number>;
  severity: string;
  confidence_base: number;
  enabled: boolean;
  is_system: boolean;
  rule_type: string;
}

export function useAlertRules() {
  return useQuery({
    queryKey: ["alert-rules"],
    queryFn: () => api<AlertRule[]>(API.ALERT_RULES.LIST),
    staleTime: 60_000,
  });
}

export function useCorrelationRules() {
  return useQuery({
    queryKey: ["correlation-rules"],
    queryFn: () => api<CorrelationRule[]>(API.CORRELATION_RULES.LIST),
    staleTime: 60_000,
  });
}

export function useAlertRuleCreateMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; rule_type: string; threshold?: number; window_minutes?: number; severity?: string }) =>
      api(API.ALERT_RULES.CREATE, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useAlertRuleUpdateMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; threshold?: number; window_minutes?: number; severity?: string; enabled?: boolean }) =>
      api(API.ALERT_RULES.UPDATE(id), { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useAlertRuleDeleteMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(API.ALERT_RULES.DELETE(id), { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useCorrelationRuleCreateMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string; rule_type?: string; event_sequence: string[]; window_minutes?: number; severity?: string }) =>
      api(API.CORRELATION_RULES.CREATE, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["correlation-rules"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}

export function useCorrelationRuleUpdateMutation(options?: { onSuccess?: () => void; onError?: (e: Error) => void }) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; name?: string; description?: string; event_sequence?: string[]; window_minutes?: number; severity?: string; enabled?: boolean }) =>
      api(API.CORRELATION_RULES.UPDATE(id), { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["correlation-rules"] });
      options?.onSuccess?.();
    },
    onError: options?.onError,
  });
}
