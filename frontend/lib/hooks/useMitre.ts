import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  MitreMatrixResponse,
  MitreDrilldownResponse,
} from "@/lib/types/mitre";

export function useMitreMatrix(params: {
  preset?: string;
  fromTime?: string;
  toTime?: string;
}) {
  const { preset, fromTime, toTime } = params;
  const qParts: string[] = [];
  if (preset) qParts.push(`preset=${preset}`);
  if (fromTime) qParts.push(`from_time=${encodeURIComponent(fromTime)}`);
  if (toTime) qParts.push(`to_time=${encodeURIComponent(toTime)}`);
  const q = qParts.length ? `?${qParts.join("&")}` : "";

  return useQuery({
    queryKey: ["mitre", "matrix", preset, fromTime, toTime],
    queryFn: () => api<MitreMatrixResponse>(`/api/v1/mitre/matrix${q}`),
    staleTime: 30_000,
  });
}

export function useMitreDrilldown(techniqueId: string | null, params: {
  preset?: string;
  fromTime?: string;
  toTime?: string;
} = {}) {
  const { preset, fromTime, toTime } = params;
  const qParts: string[] = [];
  if (preset) qParts.push(`preset=${preset}`);
  if (fromTime) qParts.push(`from_time=${encodeURIComponent(fromTime)}`);
  if (toTime) qParts.push(`to_time=${encodeURIComponent(toTime)}`);
  const q = qParts.length ? `?${qParts.join("&")}` : "";

  return useQuery({
    queryKey: ["mitre", "drilldown", techniqueId, preset, fromTime, toTime],
    queryFn: () =>
      api<MitreDrilldownResponse>(
        `/api/v1/mitre/techniques/${encodeURIComponent(techniqueId!)}/drilldown${q}`,
      ),
    enabled: !!techniqueId,
    staleTime: 15_000,
  });
}
