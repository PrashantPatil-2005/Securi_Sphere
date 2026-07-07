"use client";

import { useMemo } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { CHART_THEME, axisProps } from "@/lib/design/chartTheme";

interface HistoryPoint {
  risk_score: number;
  health_score: number;
  recorded_at: string;
}

export function HostRiskHistoryChart({ history }: { history: HistoryPoint[] }) {
  const data = useMemo(
    () =>
      history.map((h) => ({
        ...h,
        label: new Date(h.recorded_at).toLocaleString(),
      })),
    [history],
  );

  if (!data.length) return null;

  return (
    <ResponsiveContainer width="100%" height={160}>
      <LineChart data={data}>
        <CartesianGrid stroke={CHART_THEME.grid} strokeDasharray="3 3" />
        <XAxis
          dataKey="recorded_at"
          tickFormatter={(v) => {
            const d = new Date(v);
            return `${d.getMonth() + 1}/${d.getDate()}`;
          }}
          {...axisProps}
        />
        <YAxis domain={[0, 100]} {...axisProps} width={32} />
        <Tooltip {...CHART_THEME.tooltip} labelFormatter={(_, payload) => payload?.[0]?.payload?.label} />
        <Line
          type="monotone"
          dataKey="risk_score"
          name="Risk"
          stroke={CHART_THEME.colors.danger}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="health_score"
          name="Health"
          stroke={CHART_THEME.colors.success}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
