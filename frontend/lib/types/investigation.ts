export interface WorkspaceAnchor {
  type: "alert" | "offense" | "incident";
  id: string;
}

export interface WorkspaceHost {
  id: string;
  name: string;
  hostname: string | null;
  status: string;
  ip_address: string | null;
  risk_score: number | null;
}

export interface WorkspaceAlert {
  id: string;
  host_id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  confidence: number | null;
  mitre_technique_id: string | null;
  source: string | null;
  created_at: string;
}

export interface WorkspaceOffense {
  id: string;
  offense_number: number;
  host_id: string;
  host_name: string | null;
  title: string;
  description: string | null;
  risk_level: string;
  status: string;
  event_count: number;
  alert_count: number;
  incident_id: string | null;
  created_at: string | null;
  timeline: Array<Record<string, unknown>>;
  related_users: string[];
  alerts: Array<{ id: string; title: string; severity: string; status: string; created_at: string }>;
  events: Array<{ id: string; event_type: string; description: string | null; severity: string; timestamp: string }>;
}

export interface WorkspaceNote {
  id: string;
  content: string;
  user_id: string;
  user_email: string | null;
  created_at: string;
}

export interface WorkspaceIncident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  host_id: string | null;
  assigned_to: string | null;
  assignee_email: string | null;
  created_at: string;
  updated_at: string | null;
  resolved_at: string | null;
  confidence: number | null;
  first_observed: string | null;
  last_observed: string | null;
  affected_hosts: string[];
  affected_users: string[];
  affected_services: string[];
  mitre_technique_ids: string[];
  mitre_tactics: string[];
  simulated: boolean;
  source: string | null;
  notes: WorkspaceNote[];
  alert_ids: string[];
}

export interface WorkspaceEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  source: string | null;
  source_ip: string | null;
  raw_log: string | null;
  timestamp: string;
}

export interface WorkspaceTimeline {
  id: string;
  title: string;
  severity: string;
  confidence: number;
  started_at: string;
  status: string;
}

export type WorkspaceTimelineEntryType = "incident" | "alert" | "offense" | "event" | "note" | "timeline";

export interface WorkspaceTimelineEntry {
  type: WorkspaceTimelineEntryType;
  timestamp: string;
  title: string;
  description: string | null;
  severity: string | null;
  ref_id: string | null;
  simulated: boolean;
}

export interface WorkspaceEntityHost {
  id: string | null;
  name: string;
  ip: string | null;
}

export interface WorkspaceEntities {
  hosts: WorkspaceEntityHost[];
  accounts: string[];
  network_ips: string[];
}

export interface WorkspaceMitre {
  technique_ids: string[];
  tactics: string[];
}

export interface WorkspaceProvenance {
  simulated: boolean;
  sources: string[];
}

export interface InvestigationWorkspace {
  anchor: WorkspaceAnchor;
  alert: WorkspaceAlert | null;
  offense: WorkspaceOffense | null;
  incident: WorkspaceIncident | null;
  host: WorkspaceHost | null;
  events: WorkspaceEvent[];
  timelines: WorkspaceTimeline[];
  linked_alerts: WorkspaceAlert[];
  investigation_timeline: WorkspaceTimelineEntry[];
  entities: WorkspaceEntities;
  mitre: WorkspaceMitre;
  provenance: WorkspaceProvenance;
  partial_errors: string[];
}
