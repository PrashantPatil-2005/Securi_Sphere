"use client";

import { memo } from "react";
import dynamic from "next/dynamic";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { LoadingState } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { EmptyState } from "@/components/design-system/EmptyState";
import { AnimatedNumber } from "@/components/design-system/AnimatedNumber";

const PieChart = dynamic(() => import("recharts").then((mod) => mod.PieChart), { ssr: false });
const Pie = dynamic(() => import("recharts").then((mod) => mod.Pie), { ssr: false });
const Cell = dynamic(() => import("recharts").then((mod) => mod.Cell), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((mod) => mod.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(
  () => import("recharts").then((mod) => mod.ResponsiveContainer),
  { ssr: false },
);

interface SeverityData {
  total: number;
  distribution: { severity: string; count: number; percentage: number }[];
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--severity-critical)",
  high: "var(--severity-high)",
  medium: "var(--severity-medium)",
  low: "var(--severity-low)",
  info: "var(--severity-info)",
};

export const SeverityBreakdown = memo(function SeverityBreakdown() {
  const { data, isLoading, isError, refetch } = useSiemQuery<SeverityData>(
    "severity-distribution",
  );

  if (isLoading && !data) return <LoadingState variant="inline" />;
  if (isError && !data) return <ErrorState variant="inline" title="Failed to load" onRetry={() => refetch()} />;

  const dist = data?.distribution ?? [];
  const hasData = dist.some((d) => d.count > 0);

  if (!hasData) {
    return (
      <EmptyState
        title="No alerts in period"
        description="Severity distribution will populate as alerts are generated."
      />
    );
  }

  return (
    <div>
      <div className="h-[180px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={dist.filter((d) => d.count > 0)}
              dataKey="count"
              nameKey="severity"
              cx="50%"
              cy="50%"
              outerRadius={70}
              innerRadius={35}
              strokeWidth={0}
              isAnimationActive={false}
            >
              {dist
                .filter((d) => d.count > 0)
                .map((entry) => (
                  <Cell key={entry.severity} fill={SEVERITY_COLORS[entry.severity] || "var(--muted)"} />
                ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "var(--card-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "6px",
                fontSize: "12px",
              }}
              formatter={(value, name) => [`${value} alerts`, String(name)]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-3 mt-2">
        {dist.map((d) => (
          <div key={d.severity} className="flex items-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: SEVERITY_COLORS[d.severity] || "var(--muted)" }}
            />
            <span className="text-[11px] text-muted capitalize">{d.severity}</span>
            <span className="text-[11px] font-semibold tabular-nums text-foreground">
              <AnimatedNumber value={d.count} />
            </span>
          </div>
        ))}
      </div>
    </div>
  );
});
