"use client";

import { KpiCard } from "@/components/design-system/KpiCard";
import { ShieldAlert, AlertTriangle, Server, Clock } from "lucide-react";
import type { OffenseDetail } from "@/lib/types/offense";

interface Props {
  offense: OffenseDetail;
}

export function OffenseSummaryCards({ offense }: Props) {
  const relatedHostCount = offense.related_hosts?.length ?? 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <KpiCard
        label="Risk Level"
        value={offense.risk_level.charAt(0).toUpperCase() + offense.risk_level.slice(1)}
        icon={<ShieldAlert className="w-4 h-4" />}
      />
      <KpiCard
        label="Related Alerts"
        value={String(offense.alert_count)}
        icon={<AlertTriangle className="w-4 h-4" />}
      />
      <KpiCard
        label="Affected Hosts"
        value={String(relatedHostCount || 1)}
        icon={<Server className="w-4 h-4" />}
      />
      <KpiCard
        label="Events"
        value={String(offense.event_count)}
        icon={<Clock className="w-4 h-4" />}
      />
    </div>
  );
}
