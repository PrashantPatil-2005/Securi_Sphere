export interface Timeline {
  id: string;
  host_id: string;
  title: string;
  description: string | null;
  started_at: string;
  ended_at: string;
  event_ids: string[];
  mitre_techniques: string[];
  severity: string;
  confidence: number;
  status: string;
}

export interface TimelineEvent {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  mitre_technique_id: string | null;
  timestamp: string;
}

export interface TimelineFilters {
  host_id: string;
  severity: string;
  status: string;
  search: string;
}

export const DEFAULT_TIMELINE_FILTERS: TimelineFilters = {
  host_id: "",
  severity: "",
  status: "",
  search: "",
};

export const TIMELINE_SEVERITIES = ["critical", "high", "medium", "low"] as const;

export const TIMELINE_STATUSES = ["active", "resolved", "archived"] as const;

export function timelineDuration(started: string, ended: string): string {
  const ms = new Date(ended).getTime() - new Date(started).getTime();
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const remSec = sec % 60;
  if (min < 60) return `${min}m ${remSec}s`;
  const hr = Math.floor(min / 60);
  return `${hr}h ${min % 60}m`;
}
