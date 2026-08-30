export type OffenseRiskLevel = "critical" | "high" | "medium" | "low";
export type OffenseStatus = "open" | "investigating" | "resolved";

export interface OffenseSummary {
  id: string;
  offense_number: number;
  host_id: string;
  host_name: string;
  title: string;
  description: string | null;
  risk_level: OffenseRiskLevel;
  status: OffenseStatus;
  event_count: number;
  alert_count: number;
  incident_id: string | null;
  related_hosts: string[];
  related_users: string[];
  created_at: string;
  updated_at: string;
}

export interface OffenseTimelineEntry {
  ts: string;
  type: string;
  detail: string;
}

export interface OffenseAlertRef {
  id: string;
  title: string;
  severity: string;
  status: string;
  created_at: string;
}

export interface OffenseEventRef {
  id: string;
  event_type: string;
  description: string | null;
  severity: string;
  timestamp: string;
}

export interface OffenseDetail extends OffenseSummary {
  timeline: OffenseTimelineEntry[];
  alerts: OffenseAlertRef[];
  events: OffenseEventRef[];
}

export interface OffenseAiBrief {
  offense_id: string;
  brief: string;
  key_findings: string[];
  recommended_actions: string[];
  provider: string;
}

export interface OffenseListResponse {
  items: OffenseSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface OffensePromoteResponse {
  incident_id: string;
  linked_alert_count: number;
  created: boolean;
}

export interface OffenseFilters {
  status?: string;
  host_id?: string;
  q?: string;
}

export const OFFENSE_RISK_LEVELS: OffenseRiskLevel[] = ["critical", "high", "medium", "low"];
export const OFFENSE_STATUSES: OffenseStatus[] = ["open", "investigating", "resolved"];

export const OFFENSE_RISK_META: Record<OffenseRiskLevel, { label: string; color: string }> = {
  critical: { label: "Critical", color: "critical" },
  high: { label: "High", color: "high" },
  medium: { label: "Medium", color: "medium" },
  low: { label: "Low", color: "low" },
};

export const OFFENSE_STATUS_META: Record<OffenseStatus, { label: string }> = {
  open: { label: "Open" },
  investigating: { label: "Investigating" },
  resolved: { label: "Resolved" },
};
