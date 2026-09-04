"use client";

import { memo } from "react";
import {
  AlertTriangle,
  Shield,
  Server,
  Activity,
  BarChart3,
  ShieldAlert,
} from "lucide-react";
import { useSiemQuery } from "@/lib/hooks/useApiQuery";
import { KpiCard } from "@/components/design-system";
import { ErrorState } from "@/components/design-system/ErrorState";

interface ExecutiveData {
  total_hosts: number;
  online_hosts: number;
  active_alerts: number;
  critical_alerts: number;
  total_events: number;
  average_risk_score: number;
}

export const SecurityKpis = memo(function SecurityKpis() {
  const { data, isLoading, isError, refetch } = useSiemQuery<ExecutiveData>("executive");

  if (isLoading && !data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="kpi-card">
            <div className="skeleton h-3 w-20 rounded" />
            <div className="skeleton h-8 w-16 mt-2 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (isError && !data) {
    return <ErrorState variant="inline" title="Failed to load metrics" onRetry={() => refetch()} />;
  }

  const d = data!;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      <KpiCard
        label="Critical Alerts"
        value={d.critical_alerts}
        icon={<AlertTriangle className="w-4 h-4" />}
        href="/alerts"
      />
      <KpiCard
        label="Active Alerts"
        value={d.active_alerts}
        icon={<ShieldAlert className="w-4 h-4" />}
        href="/alerts"
      />
      <KpiCard
        label="Open Offenses"
        value={d.active_alerts}
        icon={<Shield className="w-4 h-4" />}
        href="/offenses"
      />
      <KpiCard
        label="Hosts Online"
        value={`${d.online_hosts}/${d.total_hosts}`}
        icon={<Server className="w-4 h-4" />}
        href="/hosts"
      />
      <KpiCard
        label="Threat Score"
        value={d.average_risk_score}
        icon={<BarChart3 className="w-4 h-4" />}
        href="/analytics"
      />
      <KpiCard
        label="Events"
        value={d.total_events?.toLocaleString() ?? "—"}
        icon={<Activity className="w-4 h-4" />}
        href="/events"
      />
    </div>
  );
});
