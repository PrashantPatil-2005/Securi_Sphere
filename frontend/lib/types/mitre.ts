export interface MitreTechnique {
  technique_id: string;
  tactic: string;
  name: string;
  description: string | null;
}

export interface MitreTechniqueWithCount extends MitreTechnique {
  count: number;
}

export interface MitreMatrixResponse {
  tactics: Record<string, MitreTechniqueWithCount[]>;
  coverage_pct: number;
  tactic_coverage: Record<string, number>;
  total_techniques: number;
}

export interface MitreDrilldownHost {
  host_id: string;
  host_name: string;
  event_count: number;
}

export interface MitreDrilldownEvent {
  id: string;
  host_id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp: string;
}

export interface MitreDrilldownAlert {
  id: string;
  host_id: string;
  title: string;
  severity: string;
  status: string;
  created_at: string;
}

export interface MitreDrilldownResponse {
  technique_id: string;
  tactic: string;
  name: string;
  description: string | null;
  event_count: number;
  alert_count: number;
  top_hosts: MitreDrilldownHost[];
  recent_events: MitreDrilldownEvent[];
  recent_alerts: MitreDrilldownAlert[];
}

export const MITRE_TACTIC_ORDER = [
  "Initial Access",
  "Execution",
  "Persistence",
  "Privilege Escalation",
  "Defense Evasion",
  "Credential Access",
  "Discovery",
  "Lateral Movement",
  "Collection",
  "Command and Control",
  "Exfiltration",
  "Impact",
] as const;
