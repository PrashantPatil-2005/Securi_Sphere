import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { API } from "@/lib/api/endpoints";
import type { Timeline, TimelineEvent } from "@/lib/types/timeline";

export function useTimelines(params: {
  page: number;
  pageSize: number;
  hostId?: string;
  preset?: string;
  fromTime?: string;
  toTime?: string;
}) {
  const { page, pageSize, hostId, preset, fromTime, toTime } = params;
  const qParts = [`page=${page}`, `page_size=${pageSize}`];
  if (hostId) qParts.push(`host_id=${hostId}`);
  if (preset) qParts.push(`preset=${preset}`);
  if (fromTime) qParts.push(`from_time=${encodeURIComponent(fromTime)}`);
  if (toTime) qParts.push(`to_time=${encodeURIComponent(toTime)}`);
  const q = qParts.length ? `?${qParts.join("&")}` : "";

  return useQuery({
    queryKey: ["timelines", page, pageSize, hostId, preset, fromTime, toTime],
    queryFn: () => api<Timeline[]>(`${API.TIMELINE.LIST}${q}`),
    staleTime: 30_000,
  });
}

export function useTimelineEvents(timelineId: string | null) {
  return useQuery({
    queryKey: ["timeline-events", timelineId],
    queryFn: () => api<TimelineEvent[]>(API.TIMELINE.EVENTS(timelineId!)),
    enabled: !!timelineId,
    staleTime: 15_000,
  });
}
