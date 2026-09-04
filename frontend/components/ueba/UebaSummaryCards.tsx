"use client";

import { memo } from "react";
import { Card } from "@/components/design-system/Card";
import { AnimatedNumber } from "@/components/design-system/AnimatedNumber";
import type { UebaSummary } from "@/lib/types/ueba";

interface UebaSummaryCardsProps {
  summary: UebaSummary | undefined;
  isLoading: boolean;
}

function UebaSummaryCardsInner({ summary, isLoading }: UebaSummaryCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 skeleton rounded-lg" />
        ))}
      </div>
    );
  }

  if (!summary) return null;

  const items = [
    { label: "Open anomalies", value: summary.open_count, color: "text-danger" },
    { label: "Critical", value: summary.by_severity?.critical ?? 0, color: "text-danger" },
    { label: "High", value: summary.by_severity?.high ?? 0, color: "text-warning" },
    { label: "Medium", value: summary.by_severity?.medium ?? 0, color: "text-severity-medium" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {items.map((item) => (
        <Card key={item.label}>
          <div className="p-3 text-center">
            <p className={`text-2xl font-semibold tabular-nums ${item.color}`}>
              <AnimatedNumber value={item.value} />
            </p>
            <p className="text-[10px] text-muted mt-1">{item.label}</p>
          </div>
        </Card>
      ))}
    </div>
  );
}

export const UebaSummaryCards = memo(UebaSummaryCardsInner);
