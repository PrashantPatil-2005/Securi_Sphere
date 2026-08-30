/**
 * Securi Sphere Chart Theme
 *
 * Theme-aware chart configuration for Recharts.
 * All colors use CSS custom properties for dark/light mode support.
 */

export const CHART_THEME = {
  grid: "var(--border-subtle)",
  axis: "var(--muted)",
  tooltip: {
    contentStyle: {
      background: "var(--card-elevated)",
      border: "1px solid var(--border)",
      borderRadius: "6px",
      fontSize: "12px",
    },
    labelStyle: { color: "var(--muted)" },
  },
  colors: {
    primary: "var(--accent)",
    danger: "var(--danger)",
    success: "var(--success)",
    warning: "var(--warning)",
  },
  severity: [
    "var(--severity-critical)",
    "var(--severity-high)",
    "var(--severity-medium)",
    "var(--severity-low)",
    "var(--severity-info)",
  ],
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

export const axisProps = {
  tick: { fontSize: 11, fill: "var(--muted)" },
  stroke: "var(--border-subtle)",
};

export const CHART_MARGINS = {
  compact: { top: 5, right: 5, bottom: 5, left: 5 },
  default: { top: 5, right: 10, bottom: 5, left: 0 },
  withLegend: { top: 5, right: 10, bottom: 20, left: 0 },
} as const;
