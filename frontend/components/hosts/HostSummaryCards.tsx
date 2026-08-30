"use client";

import { memo } from "react";
import Link from "next/link";
import { AlertTriangle, Shield, Activity, Server } from "lucide-react";
import { KpiCard } from "@/components/design-system/KpiCard";

interface HostSummaryCardsProps {
  hostId: string;
  alertCount: number | null;
  eventCount?: number;
  offenseCount?: number;
}

function HostSummaryCardsInner({ hostId, alertCount, eventCount = 0, offenseCount = 0 }: HostSummaryCardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Link href={`/alerts?host_id=${hostId}`} className="block">
        <KpiCard
          label="Open Alerts"
          value={alertCount ?? 0}
          icon={<AlertTriangle className="w-4 h-4" />}
        />
      </Link>
      <Link href={`/events?host_id=${hostId}`} className="block">
        <KpiCard
          label="Events"
          value={eventCount}
          icon={<Activity className="w-4 h-4" />}
        />
      </Link>
      <Link href={`/offenses?host_id=${hostId}`} className="block">
        <KpiCard
          label="Offenses"
          value={offenseCount}
          icon={<Shield className="w-4 h-4" />}
        />
      </Link>
      <div className="block">
        <KpiCard
          label="Host"
          value={<Server className="w-4 h-4" />}
          icon={<Server className="w-4 h-4" />}
        />
      </div>
    </div>
  );
}

export const HostSummaryCards = memo(HostSummaryCardsInner);
