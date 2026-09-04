"use client";

import { memo, useMemo } from "react";
import dynamic from "next/dynamic";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { ErrorState } from "@/components/design-system/ErrorState";
import { EmptyState } from "@/components/design-system/EmptyState";
import { ChartSkeleton } from "@/components/design-system/LoadingState";

const AreaChart = dynamic(
  () =>
    import("recharts").then((mod) => mod.AreaChart),
  { ssr: false },
);
const Area = dynamic(() => import("recharts").then((mod) => mod.Area), { ssr: false });
const XAxis = dynamic(() => import("recharts").then((mod) => mod.XAxis), { ssr: false });
const YAxis = dynamic(() => import("recharts").then((mod) => mod.YAxis), { ssr: false });
const Tooltip = dynamic(() => import("recharts").then((mod) => mod.Tooltip), { ssr: false });
const ResponsiveContainer = dynamic(
  () => import("recharts").then((mod) => mod.ResponsiveContainer),
  { ssr: false },
);

interface TrendData {
  security_trend: { period: string; count: number }[];
}

export const AlertTrendChart = memo(function AlertTrendChart() {
  const { data, isLoading, isError, refetch } = useSiemQuery<TrendData>("executive");

  const trendData = useMemo(
    () =>
      (data?.security_trend ?? [])
        .slice(-48)
        .map((p) => ({
          period: String(p.period).slice(5, 16),
          count: p.count,
        })),
    [data],
  );

  if (isLoading && !data) return <ChartSkeleton height={200} />;
  if (isError && !data) return <ErrorState variant="card" title="Failed to load trend" onRetry={() => refetch()} />;

  if (!trendData.length) {
    return (
      <EmptyState
        title="No activity data"
        description="Event volume will appear as agents report data."
      />
    );
  }

  return (
    <div className="h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={trendData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id="alertTrendGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.25} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="period" tick={{ fontSize: 10, fill: "var(--muted)" }} stroke="var(--border-subtle)" />
          <YAxis tick={{ fontSize: 10, fill: "var(--muted)" }} stroke="var(--border-subtle)" width={36} />
          <Tooltip
            contentStyle={{
              background: "var(--card-elevated)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              fontSize: "12px",
            }}
            labelStyle={{ color: "var(--muted)" }}
          />
          <Area
            type="monotone"
            dataKey="count"
            stroke="var(--accent)"
            fill="url(#alertTrendGrad)"
            strokeWidth={1.5}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
});
