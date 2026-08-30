"use client";

import { Suspense, useState } from "react";
import { useIncidentList } from "@/lib/hooks/useIncidents";
import { IncidentRow } from "@/components/incidents/IncidentRow";
import { IncidentEmptyState } from "@/components/incidents/IncidentEmptyState";
import { IncidentCreateForm } from "@/components/incidents/IncidentCreateForm";
import { IncidentDetailHeader } from "@/components/incidents/IncidentDetailHeader";
import { IncidentActions } from "@/components/incidents/IncidentActions";
import { IncidentNotes } from "@/components/incidents/IncidentNotes";
import { IncidentAlertsList } from "@/components/incidents/IncidentAlertsList";
import { useIncidentDetail } from "@/lib/hooks/useIncidents";
import { FilterChip } from "@/components/design-system/FilterChip";
import { LoadingState, Skeleton } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { Drawer } from "@/components/ui/Drawer";
import { useDeepLinkedSelection } from "@/lib/hooks/useDeepLinkedSelection";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { INCIDENT_STATUSES } from "@/lib/types/incident";

export default function IncidentsPage() {
  return (
    <Suspense fallback={<LoadingState variant="table" rows={6} />}>
      <IncidentsPageContent />
    </Suspense>
  );
}

function IncidentsPageContent() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedId, setSelectedId] = useDeepLinkedSelection();
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [showCreate, setShowCreate] = useState(false);

  const { data: items = [], isLoading, isError, refetch } = useIncidentList(
    statusFilter ? { status: statusFilter } : undefined,
  );

  const hasFilters = Boolean(statusFilter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Incidents</h1>
          <p className="text-sm text-muted mt-1">
            Security cases requiring investigation and response
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-accent text-white hover:bg-accent/90 transition-colors"
        >
          {showCreate ? "Cancel" : "New Incident"}
        </button>
      </div>

      {showCreate && (
        <div className="p-4 rounded-xl border border-border-subtle bg-surface">
          <IncidentCreateForm onCreated={() => setShowCreate(false)} />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1">
          {INCIDENT_STATUSES.map((s) => (
            <FilterChip
              key={s}
              label={s.charAt(0).toUpperCase() + s.slice(1)}
              active={statusFilter === s}
              onClick={() => setStatusFilter(statusFilter === s ? "" : s)}
            />
          ))}
        </div>
        {hasFilters && (
          <button
            type="button"
            onClick={() => setStatusFilter("")}
            className="text-xs text-muted hover:text-foreground transition-colors"
          >
            Clear
          </button>
        )}
        <span className="ml-auto text-xs text-muted">
          {items.length} incident{items.length !== 1 ? "s" : ""}
        </span>
      </div>

      {isLoading && <LoadingState variant="table" rows={4} />}
      {isError && <ErrorState variant="page" title="Failed to load incidents" onRetry={() => refetch()} />}

      {!isLoading && !isError && items.length === 0 && (
        <IncidentEmptyState hasFilters={hasFilters} onClear={() => setStatusFilter("")} />
      )}

      {!isLoading && !isError && items.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="space-y-2">
            {items.map((i) => (
              <IncidentRow
                key={i.id}
                incident={i}
                selected={selectedId === i.id}
                onClick={() => setSelectedId(i.id)}
              />
            ))}
          </div>

          <div className="hidden lg:block">
            {selectedId ? (
              <IncidentDetailInline incidentId={selectedId} />
            ) : (
              <div className="p-8 rounded-xl border border-border-subtle bg-surface text-center">
                <p className="text-sm text-muted">Select an incident to view details</p>
              </div>
            )}
          </div>
        </div>
      )}

      <Drawer
        open={!!selectedId && !isDesktop}
        onClose={() => setSelectedId(null)}
        title="Incident details"
        side="bottom"
        className="lg:hidden"
      >
        {selectedId && <IncidentDetailInline incidentId={selectedId} />}
      </Drawer>
    </div>
  );
}

function IncidentDetailInline({ incidentId }: { incidentId: string }) {
  const { data: incident, isLoading, isError, refetch } = useIncidentDetail(incidentId);

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError || !incident) {
    return <ErrorState variant="card" title="Failed to load incident" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-4">
      <IncidentDetailHeader incident={incident} />
      <IncidentActions incidentId={incident.id} currentStatus={incident.status} />
      <IncidentAlertsList alertIds={incident.alert_ids} />
      <IncidentNotes incidentId={incident.id} notes={incident.notes} />
    </div>
  );
}
