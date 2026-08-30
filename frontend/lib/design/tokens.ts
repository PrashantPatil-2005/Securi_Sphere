/**
 * Securi Sphere Design System — Tokens
 *
 * Central source of truth for design primitives.
 * All values are CSS-variable-aware for theme support.
 */

/* ─── Severity ─── */

export const SEVERITY = ["critical", "high", "medium", "low", "info"] as const;
export type Severity = (typeof SEVERITY)[number];

export const SEVERITY_META: Record<Severity, { label: string; color: string; icon: string }> = {
  critical: { label: "Critical", color: "var(--severity-critical)", icon: "AlertTriangle" },
  high: { label: "High", color: "var(--severity-high)", icon: "AlertCircle" },
  medium: { label: "Medium", color: "var(--severity-medium)", icon: "AlertTriangle" },
  low: { label: "Low", color: "var(--severity-low)", icon: "Info" },
  info: { label: "Info", color: "var(--severity-info)", icon: "Info" },
};

/* ─── Status ─── */

export const ALERT_STATUSES = ["new", "investigating", "resolved", "closed", "false_positive"] as const;
export type AlertStatus = (typeof ALERT_STATUSES)[number];

export const OFFENSE_STATUSES = ["open", "investigating", "resolved", "closed"] as const;
export type OffenseStatus = (typeof OFFENSE_STATUSES)[number];

export const HOST_STATUSES = ["online", "offline", "degraded"] as const;
export type HostStatus = (typeof HOST_STATUSES)[number];

export const INCIDENT_STATUSES = ["open", "in_progress", "resolved", "closed"] as const;
export type IncidentStatus = (typeof INCIDENT_STATUSES)[number];

export const STATUS_META: Record<string, { label: string; dot: string }> = {
  new: { label: "New", dot: "bg-accent" },
  open: { label: "Open", dot: "bg-accent" },
  investigating: { label: "Investigating", dot: "bg-warning" },
  in_progress: { label: "In Progress", dot: "bg-warning" },
  resolved: { label: "Resolved", dot: "bg-success" },
  closed: { label: "Closed", dot: "bg-muted" },
  false_positive: { label: "False Positive", dot: "bg-muted" },
  online: { label: "Online", dot: "bg-success" },
  offline: { label: "Offline", dot: "bg-danger" },
  degraded: { label: "Degraded", dot: "bg-warning" },
  healthy: { label: "Healthy", dot: "bg-success" },
  active: { label: "Active", dot: "bg-success" },
};

/* ─── Chart Colors ─── */

export const chartColors = {
  primary: "var(--accent)",
  secondary: "var(--muted)",
  success: "var(--success)",
  warning: "var(--warning)",
  danger: "var(--danger)",
  critical: "var(--severity-critical)",
  high: "var(--severity-high)",
  medium: "var(--severity-medium)",
  low: "var(--severity-low)",
  info: "var(--severity-info)",
  grid: "var(--border-subtle)",
  tooltip: { bg: "var(--card-elevated)", border: "var(--border)" },
  axis: { text: "var(--muted)", line: "var(--border-subtle)" },
  series: [
    "var(--accent)",
    "var(--success)",
    "var(--warning)",
    "var(--severity-high)",
    "var(--severity-critical)",
    "var(--muted)",
    "var(--severity-low)",
    "var(--severity-info)",
  ],
} as const;

/* ─── Entity Display Patterns ─── */

export const ENTITY_ICONS = {
  alert: "AlertTriangle",
  offense: "ShieldAlert",
  incident: "Siren",
  host: "Server",
  event: "Activity",
  rule: "FileCode2",
  mitre: "Target",
  risk: "Gauge",
  user: "User",
  notification: "Bell",
} as const;

/* ─── Typography Scale ─── */

export const TYPOGRAPHY = {
  display: { size: "2rem", weight: "700", tracking: "-0.025em", lineHeight: "1.2" },
  h1: { size: "1.5rem", weight: "600", tracking: "-0.02em", lineHeight: "1.3" },
  h2: { size: "1.125rem", weight: "600", tracking: "-0.015em", lineHeight: "1.35" },
  h3: { size: "1rem", weight: "600", tracking: "-0.01em", lineHeight: "1.4" },
  body: { size: "0.875rem", weight: "400", tracking: "0", lineHeight: "1.5" },
  caption: { size: "0.75rem", weight: "500", tracking: "0.025em", lineHeight: "1.4" },
  micro: { size: "0.625rem", weight: "600", tracking: "0.05em", lineHeight: "1.3" },
  mono: { size: "0.8125rem", weight: "400", tracking: "0", lineHeight: "1.6" },
  kpi: { size: "1.75rem", weight: "700", tracking: "-0.02em", lineHeight: "1.1" },
} as const;

/* ─── Spacing Scale ─── */

export const SPACING = {
  "2xs": "0.125rem",
  xs: "0.25rem",
  sm: "0.5rem",
  md: "0.75rem",
  lg: "1rem",
  xl: "1.5rem",
  "2xl": "2rem",
  "3xl": "3rem",
  "4xl": "4rem",
} as const;

/* ─── Border Radius ─── */

export const RADIUS = {
  none: "0",
  sm: "0.25rem",
  md: "0.375rem",
  lg: "0.5rem",
  xl: "0.75rem",
  "2xl": "1rem",
  full: "9999px",
} as const;

/* ─── Shadows ─── */

export const SHADOWS = {
  none: "none",
  xs: "0 1px 2px rgba(0,0,0,0.2)",
  sm: "0 1px 3px rgba(0,0,0,0.25)",
  md: "0 4px 12px rgba(0,0,0,0.35)",
  lg: "0 8px 24px rgba(0,0,0,0.45)",
  glow: "0 0 20px rgba(59,130,246,0.15)",
  "glow-danger": "0 0 20px rgba(239,68,68,0.2)",
  "glow-success": "0 0 20px rgba(34,197,94,0.2)",
  inset: "inset 0 1px 2px rgba(0,0,0,0.15)",
} as const;
