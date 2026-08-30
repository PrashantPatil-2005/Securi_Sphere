"use client";

import { memo } from "react";
import Link from "next/link";
import { ShieldAlert, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Card, CardHeader, SeverityBadge, StatusBadge, LoadingState, EmptyState } from "@/components/design-system";

interface AlertOffenseProps {
  offense: {
    id: string;
    offense_number: number;
    title: string;
    risk_level: string;
    status: string;
    alert_count: number;
  } | null;
  loading?: boolean;
}

function formatOffenseNumber(n: number): string {
  return `#${n.toString().padStart(4, "0")}`;
}

function AlertOffenseInner({ offense, loading }: AlertOffenseProps) {
  return (
    <Card>
      <CardHeader title="Linked Offense" />
      <div className="p-4">
        {loading ? (
          <LoadingState variant="inline" text="Loading offense\u2026" />
        ) : offense ? (
          <div className="space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1 min-w-0">
                <p className="text-xs text-muted">
                  {formatOffenseNumber(offense.offense_number)}
                </p>
                <p className="text-sm font-medium text-foreground truncate">
                  {offense.title}
                </p>
              </div>
              <SeverityBadge severity={offense.risk_level} className="shrink-0" />
            </div>

            <div className="flex items-center gap-3">
              <StatusBadge status={offense.status} />
              <span className="text-[11px] text-muted tabular-nums">
                {offense.alert_count} alert{offense.alert_count !== 1 ? "s" : ""}
              </span>
            </div>

            <Link
              href={`/offenses?id=${offense.id}`}
              className={cn(
                "inline-flex items-center gap-1.5 text-xs font-medium",
                "text-accent hover:underline",
              )}
            >
              View offense details
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        ) : (
          <EmptyState
            title="No linked offense."
            icon={<ShieldAlert className="w-5 h-5" />}
          />
        )}
      </div>
    </Card>
  );
}

export const AlertOffense = memo(AlertOffenseInner);
