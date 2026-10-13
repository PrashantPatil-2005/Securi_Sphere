"use client";

import { memo } from "react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { CHART_THEME, axisProps, CHART_MARGINS } from "@/lib/design/chartTheme";

const COLORS: Record<string, string> = {
  critical: CHART_THEME.severity[0],
  high: CHART_THEME.severity[1],
  medium: CHART_THEME.severity[2],
  low: CHART_THEME.severity[3],
  info: CHART_THEME.severity[4],
};

interface Item {
  severity: string;
  count: number;
  percentage: number;
}

function SeverityCharts({ distribution }: { distribution: Item[] }) {
  const data = distribution.filter((d) => d.count > 0);

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="severity"
              cx="50%"
              cy="50%"
              outerRadius={88}
              label={(props) => `${props.name} ${(props.payload as Item).percentage}%`}
              isAnimationActive={false}
            >
              {data.map((d) => (
                <Cell key={d.severity} fill={COLORS[d.severity] || "#888"} />
              ))}
            </Pie>
            <Tooltip contentStyle={CHART_THEME.tooltip.contentStyle} labelStyle={CHART_THEME.tooltip.labelStyle} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={CHART_MARGINS.default}>
            <XAxis dataKey="severity" {...axisProps} tick={{ fontSize: 11, fill: CHART_THEME.axis }} />
            <YAxis {...axisProps} width={32} />
            <Tooltip contentStyle={CHART_THEME.tooltip.contentStyle} labelStyle={CHART_THEME.tooltip.labelStyle} />
            <Bar dataKey="count" name="Alerts" isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.severity} fill={COLORS[d.severity] || "#888"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-3 grid grid-cols-5 gap-1.5 text-center text-[11px]">
          {distribution.map((d) => (
            <div key={d.severity} className="p-2 bg-[var(--card)] rounded border border-[var(--border-subtle)]">
              <p className="text-[var(--muted)] uppercase">{d.severity}</p>
              <p className="text-base font-semibold tabular-nums" style={{ color: COLORS[d.severity] }}>{d.percentage}%</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default memo(SeverityCharts);
