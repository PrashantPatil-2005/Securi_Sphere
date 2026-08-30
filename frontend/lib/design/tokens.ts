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
