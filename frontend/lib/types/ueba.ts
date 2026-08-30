export interface UebaAnomaly {
  id: string;
  entity_type: string;
  entity_key: string;
  entity_label: string;
  metric: string;
  observed_value: number;
  baseline_mean: number;
  baseline_stddev: number;
  z_score: number;
  severity: string;
  status: string;
  description: string;
  context: Record<string, unknown>;
  alert_id: string | null;
  detected_at: string;
  resolved_at: string | null;
}

export interface UebaSummary {
  open_count: number;
  by_severity: Record<string, number>;
  enabled: boolean;
  z_threshold: number;
  baseline_days: number;
}

export interface UebaScanResponse {
  enabled: boolean;
  created: number;
  updated: number;
  hosts_scanned: number;
  users_scanned: number;
}

export interface UebaFilters {
  status: string;
  severity: string;
  entity_type: string;
}

export const DEFAULT_UEBA_FILTERS: UebaFilters = {
  status: "open",
  severity: "",
  entity_type: "",
};

export const UEBA_ENTITY_TYPES = ["host", "user"] as const;

export const UEBA_METRICS = ["failed_logins", "auth_events", "events_total"] as const;

export const UEBA_STATUSES = ["open", "dismissed", "resolved"] as const;

export function uebaMetricLabel(metric: string): string {
  return metric.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function uebaSeverityWeight(severity: string): number {
  switch (severity) {
    case "critical": return 4;
    case "high": return 3;
    case "medium": return 2;
    case "low": return 1;
    default: return 0;
  }
}
