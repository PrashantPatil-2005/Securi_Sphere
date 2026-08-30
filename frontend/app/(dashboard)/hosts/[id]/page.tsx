"use client";

import { useParams } from "next/navigation";
import { useHostDetail, useHostRisk, useHostAlerts, useHostEvents, useHostOffenses, useHostMetrics } from "@/lib/hooks/useHosts";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { HostDetailHeader } from "@/components/hosts/HostDetailHeader";
import { HostSummaryCards } from "@/components/hosts/HostSummaryCards";
import { HostRiskSection } from "@/components/hosts/HostRiskSection";
import { HostActivityList } from "@/components/hosts/HostActivityList";
import { HostAlertsList } from "@/components/hosts/HostAlertsList";
import { HostOffensesList } from "@/components/hosts/HostOffensesList";
import { HostAgentHealth } from "@/components/hosts/HostAgentHealth";

export default function HostDetailPage() {
  const params = useParams();
  const hostId = params.id as string;

  const { data: host, isLoading: hostLoading, isError: hostError, refetch: refetchHost } = useHostDetail(hostId);
  const { data: risk, isLoading: riskLoading } = useHostRisk(hostId);
  const { data: alertsData, isLoading: alertsLoading } = useHostAlerts(hostId);
  const { data: eventsData, isLoading: eventsLoading } = useHostEvents(hostId);
  const { data: offensesData, isLoading: offensesLoading } = useHostOffenses(hostId);
  const { data: metricsData } = useHostMetrics(hostId);

  if (hostLoading) {
    return (
      <div className="space-y-4">
        <TableSkeleton rows={8} />
      </div>
    );
  }

  if (hostError || !host) {
    return <QueryError onRetry={() => refetchHost()} />;
  }

  const latestMetrics = metricsData?.[0] ?? null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <HostDetailHeader host={host} />

      {/* Summary cards */}
      <HostSummaryCards
        hostId={hostId}
        alertCount={host.alert_count}
        eventCount={eventsData?.total ?? 0}
        offenseCount={offensesData?.total ?? 0}
      />

      {/* Two-column layout: Risk + Agent Health | Activity + Alerts + Offenses */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Risk + Agent Health */}
        <div className="lg:col-span-1 space-y-6">
          <HostRiskSection risk={risk} isLoading={riskLoading} />
          <HostAgentHealth host={host} metrics={latestMetrics} />
        </div>

        {/* Right column: Activity + Alerts + Offenses */}
        <div className="lg:col-span-2 space-y-6">
          <HostActivityList
            events={eventsData?.items ?? []}
            hostId={hostId}
            total={eventsData?.total ?? 0}
            isLoading={eventsLoading}
          />
          <HostAlertsList
            alerts={alertsData?.items ?? []}
            hostId={hostId}
            total={alertsData?.total ?? 0}
            isLoading={alertsLoading}
          />
          <HostOffensesList
            offenses={offensesData?.items ?? []}
            hostId={hostId}
            total={offensesData?.total ?? 0}
            isLoading={offensesLoading}
          />
        </div>
      </div>
    </div>
  );
}
