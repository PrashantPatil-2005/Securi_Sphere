"use client";

import { memo, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { CHART_THEME, CHART_MARGINS } from "@/lib/design/chartTheme";

interface TrendPoint {
  period: string;
  count: number;
}

interface Props {
  total: TrendPoint[];
  security: TrendPoint[];
  authentication: TrendPoint[];
  service: TrendPoint[];
}

const MAX_POINTS = 120;

function formatPeriod(p: string) {
  const d = new Date(p);
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" });
}

function downsample<T>(arr: T[], max: number): T[] {
  if (arr.length <= max) return arr;
  const step = Math.ceil(arr.length / max);
  return arr.filter((_, i) => i % step === 0);
}

function mergeSeries(data: Props) {
  const keys = new Set<string>();
  for (const s of [data.total, data.security, data.authentication, data.service]) {
    s.forEach((p) => keys.add(p.period));
  }
  const map = (series: TrendPoint[]) =>
    Object.fromEntries(series.map((p) => [p.period, p.count]));
  const t = map(data.total);
  const sec = map(data.security);
  const auth = map(data.authentication);
  const svc = map(data.service);
  const merged = Array.from(keys)
    .sort()
    .map((period) => ({
      period: formatPeriod(period),
      total: t[period] ?? 0,
      security: sec[period] ?? 0,
      authentication: auth[period] ?? 0,
      service: svc[period] ?? 0,
    }));
  return downsample(merged, MAX_POINTS);
}

function EventTrendChart({ total, security, authentication, service }: Props) {
  const chartData = useMemo(
    () => mergeSeries({ total, security, authentication, service }),
    [total, security, authentication, service],
  );

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={CHART_MARGINS.default}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_THEME.grid} vertical={false} />
        <XAxis dataKey="period" tick={{ fontSize: 10, fill: CHART_THEME.axis }} stroke={CHART_THEME.grid} />
        <YAxis tick={{ fontSize: 11, fill: CHART_THEME.axis }} stroke={CHART_THEME.grid} width={40} />
        <Tooltip contentStyle={CHART_THEME.tooltip.contentStyle} labelStyle={CHART_THEME.tooltip.labelStyle} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Line type="monotone" dataKey="total" stroke={CHART_THEME.colors.primary} dot={false} strokeWidth={2} name="Total" isAnimationActive={false} />
        <Line type="monotone" dataKey="security" stroke={CHART_THEME.colors.danger} dot={false} strokeWidth={1.5} name="Security" isAnimationActive={false} />
        <Line type="monotone" dataKey="authentication" stroke={CHART_THEME.colors.warning} dot={false} strokeWidth={1.5} name="Auth" isAnimationActive={false} />
        <Line type="monotone" dataKey="service" stroke={CHART_THEME.colors.success} dot={false} strokeWidth={1.5} name="Service" isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default memo(EventTrendChart);
