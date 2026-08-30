"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Clock } from "lucide-react";
import { PageHeader } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { LoadingState } from "@/components/design-system/LoadingState";
import { EmptyState } from "@/components/design-system/EmptyState";
import { useTimelines, useTimelineEvents } from "@/lib/hooks/useTimeline";
import { TimelineList } from "@/components/timeline/TimelineList";
import { TimelineDetail } from "@/components/timeline/TimelineDetail";
import { TimelineFiltersBar } from "@/components/timeline/TimelineFilters";
import { TimelineReplay } from "@/components/timeline/TimelineReplay";
import { DEFAULT_TIMELINE_FILTERS } from "@/lib/types/timeline";
import type { TimelineFilters } from "@/lib/types/timeline";
import { useTimeRange } from "@/lib/timeRange";

export default function TimelinePage() {
  return (
    <Suspense fallback={<LoadingState rows={4} />}>
      <TimelinePageContent />
    </Suspense>
  );
}

function TimelinePageContent() {
  const searchParams = useSearchParams();
  const hostFilter = searchParams.get("host");
  const { queryParams } = useTimeRange();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filters, setFilters] = useState<TimelineFilters>(DEFAULT_TIMELINE_FILTERS);
  const [replayIndex, setReplayIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  const { data: timelines = [], isLoading, isError, refetch } = useTimelines({
    page: 1,
    pageSize: 50,
    hostId: hostFilter ?? undefined,
    preset: queryParams.preset,
    fromTime: queryParams.from_time,
    toTime: queryParams.to_time,
  });

  const { data: events = [], isLoading: eventsLoading } = useTimelineEvents(selectedId);

  const active = timelines.find((t) => t.id === selectedId);

  // Client-side filtering for search/severity/status
  const filteredTimelines = useMemo(() => {
    let result = timelines;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      result = result.filter(
        (t) =>
          t.title.toLowerCase().includes(q) ||
          (t.description && t.description.toLowerCase().includes(q)),
      );
    }
    if (filters.severity) {
      result = result.filter((t) => t.severity === filters.severity);
    }
    if (filters.status) {
      result = result.filter((t) => t.status === filters.status);
    }
    return result;
  }, [timelines, filters]);

  // Auto-select first timeline when host filter is set
  useEffect(() => {
    if (hostFilter && filteredTimelines.length > 0 && !selectedId) {
      setSelectedId(filteredTimelines[0].id);
    }
  }, [hostFilter, filteredTimelines, selectedId]);

  // Reset replay when selection changes
  useEffect(() => {
    setReplayIndex(0);
    setPlaying(false);
  }, [selectedId]);

  // Replay timer
  useEffect(() => {
    if (!playing || events.length <= 1 || replayIndex >= events.length - 1) {
      setPlaying(false);
      return;
    }
    const ms = Math.min(
      Math.max(
        (new Date(events[replayIndex + 1].timestamp).getTime() -
          new Date(events[replayIndex].timestamp).getTime()) /
          speed,
        350,
      ),
      6000,
    );
    const timer = setTimeout(() => setReplayIndex((i) => i + 1), ms);
    return () => clearTimeout(timer);
  }, [playing, replayIndex, events, speed]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    setReplayIndex(0);
    setPlaying(false);
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Attack Timelines"
        subtitle="Reconstructed attack chains — select a timeline and replay events step by step"
      />

      <TimelineFiltersBar
        filters={filters}
        onFiltersChange={setFilters}
        total={filteredTimelines.length}
      />

      {isError && <QueryError onRetry={() => refetch()} />}

      <div className="grid lg:grid-cols-[minmax(300px,1fr)_minmax(400px,1.3fr)] gap-6">
        {/* Left: Timeline list */}
        <TimelineList
          timelines={filteredTimelines}
          selectedId={selectedId}
          onSelect={handleSelect}
          isLoading={isLoading}
        />

        {/* Right: Detail + Replay */}
        <div className="space-y-6">
          <TimelineDetail
            timeline={active ?? null}
            events={events}
            isLoading={eventsLoading}
            currentIndex={replayIndex}
          />
          {active && events.length > 0 && (
            <TimelineReplay
              events={events}
              title={active.title}
              currentIndex={replayIndex}
              onIndexChange={(i) => { setPlaying(false); setReplayIndex(i); }}
              playing={playing}
              onTogglePlay={() => setPlaying((p) => !p)}
              speed={speed}
              onSpeedChange={setSpeed}
              isLoading={eventsLoading}
            />
          )}
        </div>
      </div>

      {!isLoading && !isError && timelines.length === 0 && (
        <EmptyState
          title="No attack timelines"
          description="Run a scenario in the Attack Lab or wait for correlated activity to build attack chains."
          icon={<Clock className="w-10 h-10 opacity-40" />}
          action="/simulation"
          actionLabel="Open Attack Lab"
        />
      )}
    </div>
  );
}
