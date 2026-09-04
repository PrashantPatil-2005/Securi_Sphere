"use client";

import { memo, type ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils/cn";
import { AnimatedNumber } from "./AnimatedNumber";

interface KpiCardProps {
  label: string;
  value?: ReactNode;
  delta?: number | null;
  deltaLabel?: string;
  icon?: ReactNode;
  href?: string;
  className?: string;
  loading?: boolean;
}

/** Returns the numeric interpretation of a value, or null when it isn't one. */
function toNumeric(value: ReactNode): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value.trim())) {
    const parsed = Number(value.trim());
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
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
  const reduceMotion = useReducedMotion();
  const numeric = toNumeric(value);
  const isTextual = typeof value === "string" || typeof value === "number";
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
      ) : value == null ? (
        <span className="kpi-value">{"\u2014"}</span>
      ) : numeric !== null ? (
        <span className="kpi-value">
          <AnimatedNumber value={numeric} />
        </span>
      ) : isTextual ? (
        <span className="kpi-value">
          {!reduceMotion ? (
            <motion.span
              key={String(value)}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className="inline-block"
            >
              {value}
            </motion.span>
          ) : (
            value
          )}
        </span>
      ) : (
        <span className="kpi-value">{value}</span>
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
