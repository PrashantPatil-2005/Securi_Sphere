"use client";

import { memo, type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  delta?: number | null;
  deltaLabel?: string;
  icon?: ReactNode;
  href?: string;
  className?: string;
  loading?: boolean;
}

export const KpiCard = memo(function KpiCard({
  label,
  value,
  delta,
  deltaLabel,
  icon,
  href,
  className,
  loading,
}: KpiCardProps) {
  const content = (
    <div className={cn("kpi-card group", className)}>
      <div className="flex items-center justify-between">
        <span className="kpi-label">{label}</span>
        {icon && (
          <span className="text-muted group-hover:text-foreground transition-colors [&>svg]:w-4 [&>svg]:h-4">
            {icon}
          </span>
        )}
      </div>
      {loading ? (
        <div className="skeleton h-8 w-20 mt-1 rounded" />
      ) : (
        <span className="kpi-value">{value ?? "\u2014"}</span>
      )}
      {delta != null && (
        <span
          className={cn(
            "kpi-delta",
            delta > 0
              ? "kpi-delta-up"
              : delta < 0
                ? "kpi-delta-down"
                : "kpi-delta-neutral",
          )}
        >
          {delta > 0 ? "+" : ""}
          {delta}
          {deltaLabel ? ` ${deltaLabel}` : ""}
        </span>
      )}
    </div>
  );

  if (href) {
    return (
      <a href={href} className="block">
        {content}
      </a>
    );
  }
  return content;
});
