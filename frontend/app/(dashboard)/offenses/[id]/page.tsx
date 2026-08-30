"use client";

import { useParams } from "next/navigation";
import { useOffenseDetail } from "@/lib/hooks/useOffenses";
import { OffenseDetailHeader } from "@/components/offenses/OffenseDetailHeader";
import { OffenseSummaryCards } from "@/components/offenses/OffenseSummaryCards";
import { OffenseTimeline } from "@/components/offenses/OffenseTimeline";
import { OffenseAlertsList } from "@/components/offenses/OffenseAlertsList";
import { OffenseEventsList } from "@/components/offenses/OffenseEventsList";
import { OffenseActions } from "@/components/offenses/OffenseActions";
import { Skeleton } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";

export default function OffenseDetailPage() {
  const params = useParams<{ id: string }>();
  const offenseId = params?.id ?? null;

  const { data: offense, isLoading, isError, refetch } = useOffenseDetail(offenseId);

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !offense) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <ErrorState
          variant="page"
          title="Failed to load offense"
          description={isError ? "The offense could not be loaded." : "Offense not found."}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
      <OffenseDetailHeader offense={offense} />
      <OffenseSummaryCards offense={offense} />
      <OffenseActions
        offenseId={offense.id}
        currentStatus={offense.status}
        incidentId={offense.incident_id}
      />
      <OffenseTimeline timeline={offense.timeline} />
      <OffenseAlertsList alerts={offense.alerts} />
      <OffenseEventsList events={offense.events} />
    </div>
  );
}
