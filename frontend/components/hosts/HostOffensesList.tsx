"use client";

import { memo } from "react";
import Link from "next/link";
import { Shield, ExternalLink } from "lucide-react";
import { Card, CardHeader } from "@/components/design-system/Card";
import { SeverityBadge } from "@/components/design-system/Badge";

interface HostOffense {
  id: string;
  offense_number: number;
  title: string;
  risk_level: string;
  status: string;
  created_at: string;
}

interface HostOffensesListProps {
  offenses: HostOffense[];
  hostId: string;
  total?: number;
  isLoading: boolean;
}

function HostOffensesListInner({ offenses, hostId, total = 0, isLoading }: HostOffensesListProps) {
  return (
    <Card>
      <CardHeader
        title="Offenses"
        subtitle={`${total.toLocaleString()} offenses`}
        action={
          <Link
            href={`/offenses?host_id=${hostId}`}
            className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
          >
            View all
            <ExternalLink className="w-3 h-3" />
          </Link>
        }
      />
      <div className="divide-y divide-border-subtle">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-3 w-12 skeleton rounded" />
                <div className="h-3 flex-1 skeleton rounded" />
              </div>
            ))}
          </div>
        ) : offenses.length === 0 ? (
          <div className="p-4 text-sm text-muted flex items-center gap-2">
            <Shield className="w-3.5 h-3.5 text-muted" />
            No offenses for this host.
          </div>
        ) : (
          offenses.map((offense) => (
            <Link
              key={offense.id}
              href={`/offenses/${offense.id}`}
              className="flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <SeverityBadge severity={offense.risk_level} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">
                  #{offense.offense_number} — {offense.title}
                </p>
                <p className="text-[10px] text-muted capitalize">{offense.status}</p>
              </div>
              <span className="text-[10px] text-muted tabular-nums shrink-0">
                {new Date(offense.created_at).toLocaleDateString()}
              </span>
            </Link>
          ))
        )}
      </div>
    </Card>
  );
}

export const HostOffensesList = memo(HostOffensesListInner);
