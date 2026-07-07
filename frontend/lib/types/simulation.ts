export interface MitreStepInfo {
  technique_id: string;
  tactic: string;
  name: string;
}

export interface ScenarioStep {
  order: number;
  event_type: string;
  offset_seconds: number;
  description: string | null;
  mitre: MitreStepInfo | null;
}

export interface Scenario {
  id: string;
  name: string;
  summary: string;
  difficulty: "beginner" | "intermediate" | "advanced" | string;
  event_count: number;
  duration_seconds: number;
  steps: ScenarioStep[];
  expected_alerts: string[];
  expected_outcomes: string[];
}

export interface ScenariosResponse {
  scenarios: Scenario[];
  enabled: boolean;
}

export interface EventTypeOption {
  event_type: string;
  category: string;
}

export interface EventTypesResponse {
  event_types: EventTypeOption[];
}

export interface CustomSimulationStep {
  event_type: string;
  offset_seconds: number;
  severity?: string | null;
  description?: string | null;
}

export interface CustomSimulationRequest {
  host_id: string;
  name: string;
  steps: CustomSimulationStep[];
}

export interface SimulationRunResult {
  message: string;
  events: number;
  run_id: string;
  host_id: string;
  scenario: string;
  name: string;
  event_ids: string[];
  alert_ids: string[];
  timeline_ids: string[];
  offense_ids: string[];
}

export interface SimulationRunSummary {
  id: string;
  scenario_id: string;
  name: string;
  host_id: string;
  host_name: string | null;
  event_count: number;
  alert_count: number;
  offense_count: number;
  timeline_count: number;
  created_at: string;
  run_by: string | null;
}

export interface SimulationRunListResponse {
  items: SimulationRunSummary[];
  total: number;
}

export interface SimulationRunDetail extends SimulationRunSummary {
  event_ids: string[];
  alert_ids: string[];
  timeline_ids: string[];
  offense_ids: string[];
}

export type AttackLabTab = "presets" | "custom" | "history";

export interface CustomStepDraft {
  id: string;
  event_type: string;
  offset_seconds: number;
  severity: string;
}
