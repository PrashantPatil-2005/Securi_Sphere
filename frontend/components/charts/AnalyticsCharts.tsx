"use client";

import { memo } from "react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts";
import { CHART_THEME, axisProps, CHART_MARGINS } from "@/lib/design/chartTheme";

const CAT_COLORS = [
  CHART_THEME.colors.primary,
  CHART_THEME.colors.danger,
  CHART_THEME.colors.warning,
  CHART_THEME.colors.success,
  ...CHART_THEME.series.slice(5),
];

const TOOLTIP = {
  contentStyle: CHART_THEME.tooltip.contentStyle,
  labelStyle: CHART_THEME.tooltip.labelStyle,
};

interface EventTypesData {
  categories: { category: string; count: number }[];
  trend: Record<string, unknown>[];
}

interface FailedLoginsData {
  over_time?: { period: string; count: number }[];
  top_attacking_ips?: { source_ip: string; count: number }[];
  most_targeted_accounts?: { username: string; count: number }[];
}

export const AnalyticsCharts = memo(function AnalyticsCharts({
  eventTypes,
  failedLogins,
}: {
  eventTypes: EventTypesData;
  failedLogins: FailedLoginsData;
}) {
  return (
    <>
      <div className="grid lg:grid-cols-2 gap-5">
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={eventTypes.categories} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={88} isAnimationActive={false}>
              {eventTypes.categories.map((_, i) => <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />)}
            </Pie>
            <Tooltip {...TOOLTIP} />
          </PieChart>
        </ResponsiveContainer>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={eventTypes.trend.slice(-60)} margin={CHART_MARGINS.default}>
            <XAxis dataKey="period" tick={{ fontSize: 9, fill: CHART_THEME.axis }} stroke={CHART_THEME.grid} tickFormatter={(v) => String(v).slice(5, 16)} />
            <YAxis {...axisProps} width={32} />
            <Tooltip {...TOOLTIP} />
            {eventTypes.categories.map((c, i) => (
              <Line key={c.category} type="monotone" dataKey={c.category} stroke={CAT_COLORS[i % CAT_COLORS.length]} dot={false} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={(failedLogins.over_time ?? []).slice(-60)} margin={CHART_MARGINS.default}>
            <XAxis dataKey="period" tick={{ fontSize: 9, fill: CHART_THEME.axis }} stroke={CHART_THEME.grid} tickFormatter={(v) => String(v).slice(5, 16)} />
            <YAxis {...axisProps} width={32} />
            <Tooltip {...TOOLTIP} />
            <Bar dataKey="count" fill={CHART_THEME.colors.danger} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-[11px] uppercase text-[var(--muted)] mb-2">Top attacking IPs</p>
            {(failedLogins.top_attacking_ips ?? []).slice(0, 8).map((r) => (
              <div key={r.source_ip} className="flex justify-between py-1 border-b border-[var(--border-subtle)]"><span className="font-mono text-xs">{r.source_ip}</span><span className="text-[var(--danger)]">{r.count}</span></div>
            ))}
          </div>
          <div>
            <p className="text-[11px] uppercase text-[var(--muted)] mb-2">Targeted accounts</p>
            {(failedLogins.most_targeted_accounts ?? []).slice(0, 8).map((r) => (
              <div key={r.username} className="flex justify-between py-1 border-b border-[var(--border-subtle)]"><span>{r.username}</span><span className="text-[var(--warning)]">{r.count}</span></div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
});

export default AnalyticsCharts;
