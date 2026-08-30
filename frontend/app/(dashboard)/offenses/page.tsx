"use client";

import { Suspense, useCallback, useMemo, useState } from "react";
import { useDeepLinkedSelection } from "@/lib/hooks/useDeepLinkedSelection";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { useOffenseList, useOffenseDetail } from "@/lib/hooks/useOffenses";
import { OffenseFilterBar } from "@/components/offenses/OffenseFilters";
import { OffenseRow } from "@/components/offenses/OffenseRow";
import { OffenseEmptyState } from "@/components/offenses/OffenseEmptyState";
import { OffenseDetailHeader } from "@/components/offenses/OffenseDetailHeader";
import { OffenseSummaryCards } from "@/components/offenses/OffenseSummaryCards";
import { OffenseTimeline } from "@/components/offenses/OffenseTimeline";
import { OffenseAlertsList } from "@/components/offenses/OffenseAlertsList";
import { OffenseEventsList } from "@/components/offenses/OffenseEventsList";
import { OffenseActions } from "@/components/offenses/OffenseActions";
import { Pagination, PageSizeSelect } from "@/components/design-system/Pagination";
import { LoadingState, Skeleton } from "@/components/design-system/LoadingState";
import { ErrorState } from "@/components/design-system/ErrorState";
import { Drawer } from "@/components/ui/Drawer";
import type { OffenseFilters } from "@/lib/types/offense";

export default function OffensesPage() {
  return (
    <Suspense fallback={<LoadingState variant="table" rows={6} />}>
      <OffensesPageContent />
    </Suspense>
  );
}

function OffensesPageContent() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [filters, setFilters] = useState<OffenseFilters>({});
  const [selectedId, setSelectedId] = useDeepLinkedSelection();
  const isDesktop = useMediaQuery("(min-width: 1024px)");

  const handleFiltersChange = useCallback((f: OffenseFilters) => {
    setFilters(f);
    setPage(1);
  }, []);

  const { data, isLoading, isError, refetch } = useOffenseList({
    page,
    pageSize,
    filters,
  });

  const offenses = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const hasFilters = Boolean(filters.status || filters.host_id || filters.q);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Offenses</h1>
        <p className="text-sm text-muted mt-1">
          Security activity grouped into investigation clusters
        </p>
      </div>

      <OffenseFilterBar filters={filters} onChange={handleFiltersChange} total={total} />

      {isLoading && <LoadingState variant="table" rows={6} />}
      {isError && <ErrorState variant="page" title="Failed to load offenses" onRetry={() => refetch()} />}

      {!isLoading && !isError && offenses.length === 0 && (
        <OffenseEmptyState hasFilters={hasFilters} onClear={() => handleFiltersChange({})} />
      )}

      {!isLoading && !isError && offenses.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="space-y-2">
            {offenses.map((o) => (
              <OffenseRow
                key={o.id}
                offense={o}
                selected={selectedId === o.id}
                onClick={() => setSelectedId(o.id)}
              />
            ))}
          </div>

          <div className="hidden lg:block">
            {selectedId ? (
              <OffenseDetailInline offenseId={selectedId} />
            ) : (
              <div className="p-8 rounded-xl border border-border-subtle bg-surface text-center">
                <p className="text-sm text-muted">Select an offense to view details</p>
              </div>
            )}
          </div>
        </div>
      )}

      {total > 0 && (
        <div className="flex items-center justify-between">
          <Pagination
            page={page}
            totalPages={Math.ceil(total / pageSize)}
            onPageChange={setPage}
          />
          <PageSizeSelect value={pageSize} onChange={setPageSize} />
        </div>
      )}

      <Drawer
        open={!!selectedId && !isDesktop}
        onClose={() => setSelectedId(null)}
        title="Offense details"
        side="bottom"
        className="lg:hidden"
      >
        {selectedId && <OffenseDetailInline offenseId={selectedId} />}
      </Drawer>
    </div>
  );
}

function OffenseDetailInline({ offenseId }: { offenseId: string }) {
  const { data: offense, isLoading, isError, refetch } = useOffenseDetail(offenseId);

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (isError || !offense) {
    return <ErrorState variant="card" title="Failed to load offense" onRetry={() => refetch()} />;
  }

  return (
    <div className="space-y-4">
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
