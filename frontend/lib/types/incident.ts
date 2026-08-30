export type IncidentSeverity = "critical" | "high" | "medium" | "low";
export type IncidentStatus = "open" | "investigating" | "resolved" | "closed";

export interface IncidentSummary {
  id: string;
  title: string;
  description: string | null;
  severity: IncidentSeverity;
  status: IncidentStatus;
  host_id: string | null;
  assigned_to: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface IncidentNote {
  id: string;
  content: string;
  user_id: string;
  created_at: string;
}

export interface IncidentDetail extends IncidentSummary {
  notes: IncidentNote[];
  alert_ids: string[];
}

export interface IncidentCreatePayload {
  title: string;
  description?: string;
  severity?: IncidentSeverity;
  host_id?: string;
}

export const INCIDENT_SEVERITIES: IncidentSeverity[] = ["critical", "high", "medium", "low"];
export const INCIDENT_STATUSES: IncidentStatus[] = ["open", "investigating", "resolved", "closed"];

export const INCIDENT_SEVERITY_META: Record<IncidentSeverity, { label: string; color: string }> = {
  critical: { label: "Critical", color: "critical" },
  high: { label: "High", color: "high" },
  medium: { label: "Medium", color: "medium" },
  low: { label: "Low", color: "low" },
};

export const INCIDENT_STATUS_META: Record<IncidentStatus, { label: string }> = {
  open: { label: "Open" },
  investigating: { label: "Investigating" },
  resolved: { label: "Resolved" },
  closed: { label: "Closed" },
};

/** Valid next-status transitions from a given status. */
export const INCIDENT_STATUS_TRANSITIONS: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["investigating", "resolved", "closed"],
  investigating: ["open", "resolved", "closed"],
  resolved: ["open", "investigating"],
  closed: ["open"],
};
