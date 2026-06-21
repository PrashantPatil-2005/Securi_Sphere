"use client";

import { Suspense, lazy, type ReactNode } from "react";
import { ChartSkeleton } from "./ui/Skeleton";

interface LazyWidgetProps {
  children: ReactNode;
  fallback?: ReactNode;
  minHeight?: number;
}

export function LazyWidget({ children, fallback, minHeight = 280 }: LazyWidgetProps) {
  return (
    <Suspense fallback={fallback ?? <ChartSkeleton height={minHeight} />}>
      <div style={{ minHeight }}>{children}</div>
    </Suspense>
  );
}

export const LazyEventTrendChart = lazy(() => import("@/components/charts/EventTrendChart"));
export const LazySeverityCharts = lazy(() => import("@/components/charts/SeverityCharts"));
export const LazyAnalyticsCharts = lazy(() => import("@/components/charts/AnalyticsCharts"));
