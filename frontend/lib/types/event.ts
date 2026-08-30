"use client";

/**
 * Canonical Event types matching backend EventResponse schema.
 *
 * Backend schema (schemas/event.py):
 *   id, host_id, event_type, severity, description, source, raw_log, timestamp
 *
 * The backend list endpoint also returns `total`, `page`, `page_size`, `next_cursor`, `has_more`.
 * The security_feed WebSocket broadcast includes additional fields (host_name, category, username,
 * source_ip, normalized_event) that are NOT in the REST response.
 */

export interface EventSummary {
  id: string;
  host_id: string;
  event_type: string;
  severity: string;
  description: string | null;
  source: string | null;
  raw_log: string | null;
  timestamp: string;
}

export interface EventListResponse {
  items: EventSummary[];
  total: number;
  page: number;
  page_size: number;
  next_cursor: string | null;
  has_more: boolean;
}

export interface EventTypeCount {
  event_type: string;
  count: number;
}

export interface EventFilters {
  severity: string;
  event_type: string;
  host_id: string;
  q: string;
  source_ip: string;
  username: string;
  mitre_technique_id: string;
}

export const EVENT_SEVERITIES = ["critical", "high", "medium", "low", "info"] as const;
export type EventSeverity = (typeof EVENT_SEVERITIES)[number];

export const EVENT_SORT_OPTIONS = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "severity", label: "Severity" },
] as const;

export const DEFAULT_EVENT_FILTERS: EventFilters = {
  severity: "",
  event_type: "",
  host_id: "",
  q: "",
  source_ip: "",
  username: "",
  mitre_technique_id: "",
};

export function eventHasActiveFilters(filters: EventFilters): boolean {
  return Object.values(filters).some(Boolean);
}

/** Count of active filters (excluding q and mitre_technique_id which are set via URL). */
export function eventActiveFilterCount(filters: EventFilters): number {
  return [filters.severity, filters.event_type, filters.host_id, filters.source_ip, filters.username].filter(Boolean).length;
}
