"use client";

import { useParams } from "next/navigation";
import { useIncidentDetail } from "@/lib/hooks/useIncidents";
import { IncidentDetailHeader } from "@/components/incidents/IncidentDetailHeader";
import { IncidentActions } from "@/components/incidents/IncidentActions";
import { IncidentNotes } from "@/components/incidents/IncidentNotes";
import { IncidentAlertsList } from "@/components/incidents/IncidentAlertsList";
import { Skeleton } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const incidentId = params?.id ?? null;

  const { data: incident, isLoading, isError, refetch } = useIncidentDetail(incidentId);

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

  if (isError || !incident) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <ErrorState
          variant="page"
          title="Failed to load incident"
          description={isError ? "The incident could not be loaded." : "Incident not found."}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
      <IncidentDetailHeader incident={incident} />
      <IncidentActions incidentId={incident.id} currentStatus={incident.status} />
      <IncidentAlertsList alertIds={incident.alert_ids} />
      <IncidentNotes incidentId={incident.id} notes={incident.notes} />
    </div>
  );
}
