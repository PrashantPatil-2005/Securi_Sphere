/** SecuriSphere Design System Tokens */

export const spacing = {
  xs: "0.25rem",   // 4px
  sm: "0.5rem",    // 8px
  md: "1rem",      // 16px
  lg: "1.5rem",    // 24px
  xl: "2rem",      // 32px
  "2xl": "3rem",   // 48px
} as const;

export const radius = {
  sm: "0.25rem",
  md: "0.375rem",
  lg: "0.5rem",
  xl: "0.75rem",
  full: "9999px",
} as const;

export const shadows = {
  sm: "0 1px 2px rgba(0,0,0,0.25)",
  md: "0 4px 12px rgba(0,0,0,0.35)",
  lg: "0 8px 24px rgba(0,0,0,0.45)",
  glow: "0 0 20px rgba(76,154,255,0.15)",
} as const;

export const typography = {
  display: { size: "2rem", weight: 700, tracking: "-0.025em", lineHeight: 1.2 },
  heading: { size: "1.25rem", weight: 600, tracking: "-0.015em", lineHeight: 1.3 },
  subheading: { size: "0.875rem", weight: 600, tracking: "0.01em", lineHeight: 1.4 },
  body: { size: "0.875rem", weight: 400, tracking: "0", lineHeight: 1.5 },
  caption: { size: "0.75rem", weight: 500, tracking: "0.025em", lineHeight: 1.4 },
} as const;

export const chartColors = {
  primary: "#4c9aff",
  secondary: "#7b8ba3",
  success: "#3dd68c",
  warning: "#f5c842",
  danger: "#ff6b6b",
  critical: "#ff4757",
  high: "#ff8c42",
  medium: "#f5c842",
  low: "#4c9aff",
  info: "#7b8ba3",
  grid: "#243044",
  tooltip: { bg: "#111820", border: "#243044" },
} as const;

export const animation = {
  fast: 150,
  normal: 200,
  slow: 300,
  easing: [0.4, 0, 0.2, 1] as const,
} as const;
