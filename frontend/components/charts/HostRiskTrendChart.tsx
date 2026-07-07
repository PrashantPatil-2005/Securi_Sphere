"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from "recharts";
import { CHART_THEME, axisProps } from "@/lib/design/chartTheme";
import { chartColors } from "@/lib/design/tokens";

const SERIES_COLORS = [
  CHART_THEME.colors.danger,
  CHART_THEME.colors.warning,
  CHART_THEME.colors.primary,
  "#a78bfa",
  "#f472b6",
  "#34d399",
  "#fb923c",
  "#38bdf8",
];

interface TrendPoint {
  recorded_at: string;
  risk_score: number;
  health_score: number;
}

interface HostSeries {
  host_id: string;
  host_name: string;
  current_score: number;
  delta: number;
  points: TrendPoint[];
}

interface FleetPoint {
  period: string;
  avg_risk: number;
  avg_health: number;
}

interface HostRiskTrendChartProps {
  fleetAverage: FleetPoint[];
  series: HostSeries[];
  showFleet?: boolean;
}

function formatTick(iso: string) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:00`;
}

export function HostRiskTrendChart({ fleetAverage, series, showFleet = true }: HostRiskTrendChartProps) {
  const chartData = useMemo(() => {
    const keys = new Set<string>();
    const rows = new Map<string, Record<string, string | number>>();

    if (showFleet) {
      for (const p of fleetAverage) {
        keys.add(p.period);
        const row = rows.get(p.period) ?? { period: p.period };
        row.fleet = p.avg_risk;
        rows.set(p.period, row);
      }
    }

    series.forEach((s) => {
      for (const p of s.points) {
        keys.add(p.recorded_at);
        const row = rows.get(p.recorded_at) ?? { period: p.recorded_at };
        row[s.host_name] = p.risk_score;
        rows.set(p.recorded_at, row);
      }
    });

    return Array.from(rows.values()).sort(
      (a, b) => new Date(String(a.period)).getTime() - new Date(String(b.period)).getTime(),
    );
  }, [fleetAverage, series, showFleet]);

  if (!chartData.length) {
    return <p className="text-sm text-muted">No risk score history in this time range.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData}>
        <CartesianGrid stroke={CHART_THEME.grid} strokeDasharray="3 3" />
        <XAxis dataKey="period" tickFormatter={formatTick} {...axisProps} />
        <YAxis domain={[0, 100]} {...axisProps} width={36} />
        <Tooltip
          {...CHART_THEME.tooltip}
          labelFormatter={(v) => new Date(String(v)).toLocaleString()}
        />
        <Legend />
        {showFleet && (
          <Line
            type="monotone"
            dataKey="fleet"
            name="Fleet avg"
            stroke={chartColors.secondary}
            strokeWidth={2}
            strokeDasharray="6 4"
            dot={false}
            isAnimationActive={false}
          />
        )}
        {series.map((s, i) => (
          <Line
            key={s.host_id}
            type="monotone"
            dataKey={s.host_name}
            stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
