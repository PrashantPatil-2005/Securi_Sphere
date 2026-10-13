/** Operational health and agent-status types (Phase 9). */

export type ComponentHealthState = "healthy" | "degraded" | "unavailable" | "unknown";

export interface HealthComponent {
  id: string;
  name: string;
  status: ComponentHealthState;
  message: string;
  impaired: string[];
  next_action: string | null;
  last_checked: string;
  detail: Record<string, string | number | boolean | null>;
}

export interface ComponentHealthResponse {
  overall: ComponentHealthState;
  environment: string;
  timestamp: string;
  components: HealthComponent[];
}

export interface HostDeliveryStats {
  buffered_events?: number;
  last_flush_at?: string | null;
  last_success_at?: string | null;
  consecutive_failures?: number;
  dropped_events?: number;
  auth_failed?: boolean;
  flows_enabled?: boolean;
  reported_at?: string;
}

export interface HostAgentStatus {
  host_id: string;
  name: string;
  hostname: string | null;
  ip_address: string | null;
  os_info: string | null;
  status: string;
  enrolled: boolean;
  api_key_created_at: string | null;
  api_key_revoked_at: string | null;
  pending_enrollment_tokens: number;
  agent_version: string | null;
  integrity_recorded: boolean;
  agent_hash_changed_at: string | null;
  last_seen: string | null;
  heartbeat_state: "recent" | "stale" | "never";
  heartbeat_age_seconds: number | null;
  last_event_at: string | null;
  last_metric_at: string | null;
  flow_collector_active: boolean;
  flow_count_24h: number;
  last_flow_at: string | null;
  delivery_stats: HostDeliveryStats | null;
  delivery_stats_source: "agent_heartbeat" | null;
  checked_at: string;
  messages: string[];
}

export interface SimulationReadinessHost {
  host_id: string;
  name: string;
  os_info: string | null;
  enrolled: boolean;
  heartbeat_state: "recent" | "stale" | "never";
  heartbeat_age_seconds: number | null;
  last_seen: string | null;
  flow_collector_required: boolean;
  flow_collector_active: boolean | null;
  provenance: "live";
}

export interface SimulationReadiness {
  scenario_id: string;
  scenario_name: string;
  required_telemetry: string[];
  synthetic_ready: boolean;
  synthetic_note: string;
  live_ready: boolean;
  live_reasons: string[];
  host: SimulationReadinessHost | null;
  backend: {
    overall: ComponentHealthState;
    impaired_components: string[];
    timestamp: string;
  };
  checked_at: string;
}
