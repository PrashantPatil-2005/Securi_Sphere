/**
 * Canonical Host types matching backend HostResponse schema.
 *
 * Backend schema (schemas/host.py):
 *   id, name, hostname, ip_address, os_info, status, enrolled,
 *   last_seen, created_at, risk_score, alert_count
 */

export interface HostSummary {
  id: string;
  name: string;
  hostname: string | null;
  ip_address: string | null;
  os_info: string | null;
  status: string;
  enrolled: boolean;
  last_seen: string | null;
  created_at: string;
  risk_score: number | null;
  alert_count: number | null;
}

export interface HostListResponse {
  items: HostSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface HostRiskFactor {
  name: string;
  value: number;
  weight: number;
}

export interface HostRiskHistoryPoint {
  risk_score: number;
  health_score: number;
  recorded_at: string;
}

export interface HostRiskDetail {
  host_id: string;
  host_name: string;
  score: number;
  health_score: number;
  factors: Record<string, number>;
  factor_breakdown: HostRiskFactor[];
  history: HostRiskHistoryPoint[];
}

export interface HostFilters {
  hostname: string;
  status: string;
  os_info: string;
  min_risk: string;
  max_risk: string;
}

export const HOST_STATUSES = ["inactive", "online", "offline", "warning", "critical"] as const;
export type HostStatus = (typeof HOST_STATUSES)[number];

export const HOST_SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "host_name", label: "Name A–Z" },
  { value: "risk_score", label: "Risk score" },
  { value: "alert_count", label: "Alert count" },
] as const;

export const DEFAULT_HOST_FILTERS: HostFilters = {
  hostname: "",
  status: "",
  os_info: "",
  min_risk: "",
  max_risk: "",
};

export function hostStatusColor(status: string): string {
  switch (status) {
    case "online": return "text-success";
    case "offline": return "text-muted";
    case "warning": return "text-warning";
    case "critical": return "text-danger";
    case "inactive": return "text-muted";
    default: return "text-muted";
  }
}

export function hostRiskLevel(score: number | null): string {
  if (score === null) return "none";
  if (score >= 70) return "critical";
  if (score >= 40) return "high";
  if (score >= 20) return "medium";
  return "low";
}

export function hostRiskColor(score: number | null): string {
  if (score === null) return "text-muted";
  if (score >= 70) return "text-danger";
  if (score >= 40) return "text-warning";
  if (score >= 20) return "text-severity-medium";
  return "text-success";
}
