"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { useEventCursorList } from "@/lib/hooks/useEvents";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import ExportMenu from "@/components/export/ExportMenu";
import CursorPaginationBar from "@/components/pagination/CursorPaginationBar";
import TimeRangeBar from "@/components/filters/TimeRangeBar";
import { PageHeader } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { PageSizeSelect } from "@/components/design-system/Pagination";
import { EventFiltersBar } from "@/components/events/EventFilters";
import { EventRow } from "@/components/events/EventRow";
import { EventEmptyState } from "@/components/events/EventEmptyState";
import { EventDetailDrawer } from "@/components/events/EventDetailDrawer";
import { DEFAULT_EVENT_FILTERS } from "@/lib/types/event";
import type { EventFilters, EventSummary } from "@/lib/types/event";

export default function EventsPage() {
  return (
    <Suspense fallback={<TableSkeleton />}>
      <EventsPageContent />
    </Suspense>
  );
}

function EventsPageContent() {
  const searchParams = useSearchParams();
  const { queryParams } = useTimeRange();
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [filters, setFilters] = useState<EventFilters>(DEFAULT_EVENT_FILTERS);
  const [selectedEvent, setSelectedEvent] = useState<EventSummary | null>(null);

  // Read URL params on mount
  useEffect(() => {
    const mitre = searchParams.get("mitre_technique_id");
    const hostId = searchParams.get("host_id");
    if (mitre || hostId) {
      setFilters((prev) => ({
        ...prev,
        ...(mitre ? { mitre_technique_id: mitre } : {}),
        ...(hostId ? { host_id: hostId } : {}),
      }));
    }
  }, [searchParams]);

  // Debounce search and event type filters
  const debouncedQ = useDebounce(filters.q, 400);
  const debouncedSourceType = useDebounce(filters.source_ip, 400);
  const debouncedUsername = useDebounce(filters.username, 400);
  const debouncedFilters = useMemo(
    () => ({
      ...filters,
      q: debouncedQ,
      source_ip: debouncedSourceType,
      username: debouncedUsername,
    }),
    [filters, debouncedQ, debouncedSourceType, debouncedUsername],
  );

  const {
    items,
    total,
    isLoading,
    isFetching,
    isError,
    refetch,
    page,
    hasMore,
    goNext,
    goPrev,
  } = useEventCursorList({
    pageSize,
    sort,
    filters: debouncedFilters,
  });

  const exportQuery = buildQuery({ sort, ...debouncedFilters }, queryParams);

  const handleClearFilters = useCallback(() => {
    setFilters(DEFAULT_EVENT_FILTERS);
  }, []);

  const handleSelectEvent = useCallback((event: EventSummary) => {
    setSelectedEvent(event);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setSelectedEvent(null);
  }, []);

  return (
    <div>
      <PageHeader
        title="Events"
        subtitle="Security telemetry and observed activity"
        action={<ExportMenu resource="events" query={exportQuery} />}
      />

      <TimeRangeBar />

      <div className="mt-4">
        <EventFiltersBar
          filters={filters}
          sort={sort}
          onFiltersChange={setFilters}
          onSortChange={setSort}
          total={total}
        />
      </div>

      <div className="mt-4">
        {isLoading ? (
          <TableSkeleton rows={12} />
        ) : isError ? (
          <QueryError onRetry={() => refetch()} />
        ) : items.length === 0 ? (
          <EventEmptyState
            hasFilters={Object.values(debouncedFilters).some(Boolean)}
            onClear={handleClearFilters}
          />
        ) : (
          <>
            <div className={`transition-opacity ${isFetching ? "opacity-70" : ""}`}>
              {/* Desktop table header */}
              <div className="hidden md:flex items-center gap-3 px-3 py-2 border-b border-border-subtle text-[11px] font-medium text-muted uppercase tracking-wide">
                <span className="w-[68px] shrink-0">Time</span>
                <span className="w-[70px] shrink-0">Severity</span>
                <span className="flex-1">Event</span>
                <span className="w-[80px] shrink-0 hidden lg:block text-right">Host</span>
              </div>

              {/* Event rows */}
              <div>
                {items.map((event) => (
                  <EventRow
                    key={event.id}
                    event={event}
                    selected={selectedEvent?.id === event.id}
                    onClick={handleSelectEvent}
                  />
                ))}
              </div>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4 px-1">
              <div className="flex items-center gap-3">
                <CursorPaginationBar
                  page={page}
                  pageSize={pageSize}
                  total={total}
                  itemCount={items.length}
                  hasMore={hasMore}
                  onPrev={goPrev}
                  onNext={goNext}
                  onPageSize={setPageSize}
                />
              </div>
              <PageSizeSelect value={pageSize} onChange={setPageSize} />
            </div>
          </>
        )}
      </div>

      {/* Event detail drawer */}
      <EventDetailDrawer
        event={selectedEvent}
        open={!!selectedEvent}
        onClose={handleCloseDrawer}
      />
    </div>
  );
}
