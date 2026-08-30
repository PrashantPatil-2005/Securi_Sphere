/**
 * Canonical alert types matching the backend AlertResponse schema.
 * All alert-related components should import from here.
 */

export interface Alert {
  id: string;
  host_id: string;
  rule_id: string | null;
  source: string | null;
  mitre_technique_id: string | null;
  mitre_tactic: string | null;
  confidence: number | null;
  severity: string;
  title: string;
  description: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
  resolved_by: string | null;
  assigned_to: string | null;
  feedback_label: string | null;
  feedback_note: string | null;
  feedback_at: string | null;
  feedback_by: string | null;
}

export interface AlertListResponse {
  items: Alert[];
  total: number;
  page: number;
  page_size: number;
}

export interface AlertHost {
  id: string;
  name: string;
  hostname: string | null;
  status: string;
  ip_address: string | null;
  risk_score: number | null;
}

export interface AlertEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp: string;
}

export interface AlertTimeline {
  id: string;
  title: string;
  severity: string;
  confidence: number;
  started_at: string;
  status: string;
}

export interface InvestigationData {
  alert: Alert;
  host: AlertHost;
  events: AlertEvent[];
  timelines: AlertTimeline[];
}

export interface AlertAiSummary {
  alert_id: string;
  summary: string;
  investigation_steps: string[];
  recommended_actions: string[];
  provider: string;
}

export interface AlertFilters {
  status: string;
  severity: string;
  host_id: string;
  rule_name: string;
  q: string;
  mitre_technique_id: string;
}

export const ALERT_STATUSES = ["open", "investigating", "resolved", "closed"] as const;
export const ALERT_SEVERITIES = ["critical", "high", "medium", "low"] as const;

export type AlertStatus = (typeof ALERT_STATUSES)[number];
