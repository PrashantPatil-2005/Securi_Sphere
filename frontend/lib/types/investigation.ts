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
  timeline: Array<Record<string, unknown>>;
  related_users: string[];
  alerts: Array<{ id: string; title: string; severity: string; status: string; created_at: string }>;
  events: Array<{ id: string; event_type: string; description: string | null; severity: string; timestamp: string }>;
}

export interface WorkspaceIncident {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  status: string;
  host_id: string | null;
  created_at: string;
  resolved_at: string | null;
  notes: Array<{ id: string; content: string; user_id: string; created_at: string }>;
  alert_ids: string[];
}

export interface WorkspaceEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
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

export interface InvestigationWorkspace {
  anchor: WorkspaceAnchor;
  alert: WorkspaceAlert | null;
  offense: WorkspaceOffense | null;
  incident: WorkspaceIncident | null;
  host: WorkspaceHost | null;
  events: WorkspaceEvent[];
  timelines: WorkspaceTimeline[];
  linked_alerts: WorkspaceAlert[];
}
