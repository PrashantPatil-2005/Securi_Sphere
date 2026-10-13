"use client";

import Link from "next/link";
import { Briefcase } from "lucide-react";
import { useIncidentDetail } from "@/lib/hooks/useIncidents";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { IncidentDetailHeader } from "./IncidentDetailHeader";
import { IncidentAlertsList } from "./IncidentAlertsList";
import { IncidentNotes } from "./IncidentNotes";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";

interface Props {
  incidentId: string | null;
  onStatus: (id: string, status: string) => void;
  isUpdating?: boolean;
}

export function IncidentInvestigationPane({ incidentId, onStatus, isUpdating }: Props) {
  const { data, isLoading, isError, refetch } = useIncidentDetail(incidentId);

  if (!incidentId) {
    return (
      <Panel title="Incident investigation">
        <EmptyState
          title="Select an incident"
          description="Choose an incident from the list to review linked alerts, add notes, and advance its status."
        />
      </Panel>
    );
  }

  if (isLoading) {
    return (
      <Panel title="Incident investigation">
        <TableSkeleton rows={5} />
      </Panel>
    );
  }

  if (isError || !data) {
    return (
      <Panel title="Incident investigation">
        <QueryError onRetry={() => refetch()} />
      </Panel>
    );
  }

  return (
    <div className="space-y-4">
      <IncidentDetailHeader
        incident={data}
        onStatusChange={(status: string) => onStatus(data.id, status)}
        isUpdating={isUpdating}
      />

      <IncidentAlertsList alertIds={data.alert_ids} />
      <IncidentNotes incidentId={data.id} notes={data.notes} />

      <div className="flex flex-wrap gap-2">
        <Link href={workspaceHref({ incidentId: data.id })} className="btn-primary text-xs inline-flex">
          <Briefcase className="w-3.5 h-3.5 mr-1.5" />
          Open Case Workspace
        </Link>
        <Link href={`/incidents/${data.id}`} className="btn-ghost text-xs">
          Full incident view
        </Link>
      </div>
    </div>
  );
}
