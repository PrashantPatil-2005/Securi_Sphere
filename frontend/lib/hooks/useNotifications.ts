"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface NotificationItem {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  severity: string | null;
  resource_type: string | null;
  resource_id: string | null;
  created_at: string;
  read: boolean;
}

interface HistoryResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
}

export function useNotificationHistory(page = 1, pageSize = 20, unreadOnly = false) {
  return useQuery({
    queryKey: ["notifications", "history", page, pageSize, unreadOnly],
    queryFn: () =>
      api<HistoryResponse>(
        `/api/v1/notifications/history?page=${page}&page_size=${pageSize}&unread_only=${unreadOnly}`,
      ),
    staleTime: 30_000,
  });
}

export function useUnreadNotificationCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api<{ unread_count: number }>("/api/v1/notifications/unread-count"),
    staleTime: 15_000,
    refetchInterval: 60_000,
  });
}

export function useNotificationMutations() {
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };

  const markRead = useMutation({
    mutationFn: (id: string) =>
      api(`/api/v1/notifications/${id}/read`, { method: "PATCH" }),
    onSuccess: invalidate,
  });

  const markAllRead = useMutation({
    mutationFn: () => api<{ marked: number }>("/api/v1/notifications/read-all", { method: "POST" }),
    onSuccess: invalidate,
  });

  return { markRead, markAllRead };
}

export function notificationHref(item: NotificationItem): string | null {
  if (item.resource_type === "alert" && item.resource_id) {
    return `/investigation?alert=${item.resource_id}`;
  }
  if (item.resource_type === "offense" && item.resource_id) {
    return `/investigation?offense=${item.resource_id}`;
  }
  if (item.resource_type === "incident" && item.resource_id) {
    return `/investigation?incident=${item.resource_id}`;
  }
  return null;
}
