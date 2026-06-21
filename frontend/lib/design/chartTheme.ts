import { chartColors } from "@/lib/design/tokens";

export const CHART_THEME = {
  grid: chartColors.grid,
  axis: chartColors.secondary,
  tooltip: {
    contentStyle: {
      background: chartColors.tooltip.bg,
      border: `1px solid ${chartColors.tooltip.border}`,
      borderRadius: "6px",
      fontSize: "12px",
    },
    labelStyle: { color: chartColors.secondary },
  },
  colors: {
    primary: chartColors.primary,
    danger: chartColors.danger,
    success: chartColors.success,
    warning: chartColors.warning,
  },
  severity: [chartColors.critical, chartColors.high, chartColors.medium, chartColors.low, chartColors.info],
} as const;

export const axisProps = {
  tick: { fontSize: 11, fill: chartColors.secondary },
  stroke: chartColors.grid,
};
