"use client";

import { Suspense, useCallback } from "react";
import Link from "next/link";
import { Briefcase } from "lucide-react";
import { useParams, useSearchParams } from "next/navigation";
import { useIncidentDetail, useIncidentStatusMutation } from "@/lib/hooks/useIncidents";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { useToast } from "@/components/ui/Toast";
import { IncidentDetailHeader } from "@/components/incidents/IncidentDetailHeader";
import { IncidentAlertsList } from "@/components/incidents/IncidentAlertsList";
import { IncidentNotes } from "@/components/incidents/IncidentNotes";
import { Panel } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/design-system/EmptyState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { InvestigationTrail } from "@/components/InvestigationTrail";
import { useUser } from "@/lib/hooks/useUser";
import type { IncidentDetail } from "@/lib/types/incident";

export default function IncidentDetailPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={8} />}>
      <IncidentDetailContent />
    </Suspense>
  );
}

function IncidentDetailContent() {
  const { incidentId: paramId } = useParams<{ incidentId: string }>();
  const searchParams = useSearchParams();
  const effectiveId = paramId || searchParams.get("incident");

  const { toast } = useToast();
  const { data: user } = useUser();
  const canMutate = user?.role?.name === "admin" || user?.role?.name === "analyst";

  const { data, isLoading, isError, refetch } = useIncidentDetail(effectiveId);

  const statusMutation = useIncidentStatusMutation({
    onSuccess: () => toast("success", "Incident status updated"),
    onError: (e) => toast("error", "Failed to update status", e.message),
  });

  const handleStatus = useCallback(
    (status: string) => {
      if (effectiveId) statusMutation.mutate({ id: effectiveId, status });
    },
    [effectiveId, statusMutation],
  );

  if (!effectiveId) {
    return (
      <EmptyState
        title="Incident not found"
        description="No incident id was provided in the URL."
        actionLabel="Back to incidents"
        action="/incidents"
      />
    );
  }

  if (isLoading) {
    return <TableSkeleton rows={8} />;
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Failed to load incident"
        description="It may have been deleted or you may not have permission to view it."
        onRetry={() => refetch()}
      />
    );
  }

  const incident: IncidentDetail = data;

  return (
    <div className="space-y-6">
      <IncidentDetailHeader
        incident={incident}
        onStatusChange={canMutate ? handleStatus : undefined}
        isUpdating={statusMutation.isPending}
      />

      <div className="grid lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,1fr)] gap-6 items-start">
        <div className="space-y-6">
          <IncidentAlertsList alertIds={incident.alert_ids} />
          <IncidentNotes incidentId={incident.id} notes={incident.notes} />

          <Panel title="Timeline">
            <div className="text-sm text-muted">
              <p>
                Created:{" "}
                <span className="text-foreground">
                  {new Date(incident.created_at).toLocaleString()}
                </span>
              </p>
              {incident.resolved_at ? (
                <p className="mt-1">
                  Resolved:{" "}
                  <span className="text-foreground">
                    {new Date(incident.resolved_at).toLocaleString()}
                  </span>
                </p>
              ) : (
                <p className="mt-1">Not yet resolved.</p>
              )}
            </div>
          </Panel>
        </div>

        <div className="hidden lg:block lg:sticky lg:top-20 space-y-6">
          <Link
            href={workspaceHref({ incidentId: incident.id })}
            className="btn-primary text-sm inline-flex w-full justify-center"
          >
            <Briefcase className="w-4 h-4 mr-1.5" />
            Open Case Workspace
          </Link>
          <Panel title="Case navigator">
            <InvestigationTrail
              incidentId={incident.id}
              hostId={incident.host_id ?? undefined}
              alertId={incident.alert_ids?.[0]}
            />
          </Panel>
        </div>
      </div>
    </div>
  );
}
