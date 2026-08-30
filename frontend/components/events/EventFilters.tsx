"use client";

import { memo, useCallback } from "react";
import { SearchBar } from "@/components/design-system/SearchBar";
import { FilterChip } from "@/components/design-system/FilterChip";
import { FilterGroup } from "@/components/design-system/FilterChip";
import { Select } from "@/components/design-system/Select";
import { Button } from "@/components/design-system/Button";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { useEventTypes } from "@/lib/hooks/useEvents";
import { EVENT_SEVERITIES, EVENT_SORT_OPTIONS } from "@/lib/types/event";
import type { EventFilters } from "@/lib/types/event";

interface EventFiltersBarProps {
  filters: EventFilters;
  sort: string;
  onFiltersChange: (filters: EventFilters) => void;
  onSortChange: (sort: string) => void;
  total: number;
}

function EventFiltersBarInner({
  filters,
  sort,
  onFiltersChange,
  onSortChange,
  total,
}: EventFiltersBarProps) {
  const { data: hosts = [] } = useHostsList();
  const { data: eventTypes = [] } = useEventTypes();

  const updateFilter = useCallback(
    (key: keyof EventFilters, value: string) => {
      onFiltersChange({ ...filters, [key]: value });
    },
    [filters, onFiltersChange],
  );

  const clearAll = useCallback(() => {
    onFiltersChange({
      severity: "",
      event_type: "",
      host_id: "",
      q: "",
      source_ip: "",
      username: "",
      mitre_technique_id: "",
    });
  }, [onFiltersChange]);

  const activeCount = [
    filters.severity,
    filters.event_type,
    filters.host_id,
    filters.source_ip,
    filters.username,
  ].filter(Boolean).length;

  return (
    <div className="space-y-3">
      {/* Search row */}
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchBar
          placeholder="Search events by keyword, type, description, or raw log..."
          value={filters.q}
          onChange={(v) => updateFilter("q", v)}
          className="flex-1"
        />
        <div className="flex gap-2 items-center">
          <Select
            value={sort}
            onChange={(e) => onSortChange(e.target.value)}
            className="!w-auto !text-xs"
            aria-label="Sort events"
          >
            {EVENT_SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>
          <span className="text-xs text-muted tabular-nums whitespace-nowrap">
            {total.toLocaleString()} events
          </span>
        </div>
      </div>

      {/* Filter chips row */}
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={filters.severity}
          onChange={(e) => updateFilter("severity", e.target.value)}
          className="!w-auto !text-xs min-w-[110px]"
          aria-label="Filter by severity"
        >
          <option value="">All severities</option>
          {EVENT_SEVERITIES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </Select>

        <Select
          value={filters.host_id}
          onChange={(e) => updateFilter("host_id", e.target.value)}
          className="!w-auto !text-xs min-w-[130px]"
          aria-label="Filter by host"
        >
          <option value="">All hosts</option>
          {hosts.map((h) => (
            <option key={h.id} value={h.id}>{h.name}</option>
          ))}
        </Select>

        <Select
          value={filters.event_type}
          onChange={(e) => updateFilter("event_type", e.target.value)}
          className="!w-auto !text-xs min-w-[140px]"
          aria-label="Filter by event type"
        >
          <option value="">All event types</option>
          {eventTypes.map((t) => (
            <option key={t.event_type} value={t.event_type}>
              {t.event_type} ({t.count.toLocaleString()})
            </option>
          ))}
        </Select>

        <input
          type="text"
          placeholder="Source IP"
          value={filters.source_ip}
          onChange={(e) => updateFilter("source_ip", e.target.value)}
          className="input-siem !w-auto !text-xs !py-1 min-w-[110px]"
          aria-label="Filter by source IP"
        />

        <input
          type="text"
          placeholder="Username"
          value={filters.username}
          onChange={(e) => updateFilter("username", e.target.value)}
          className="input-siem !w-auto !text-xs !py-1 min-w-[110px]"
          aria-label="Filter by username"
        />

        {activeCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAll}
            className="text-xs"
          >
            Clear all ({activeCount})
          </Button>
        )}

        {/* Active filter chips */}
        <FilterGroup>
          {filters.severity && (
            <FilterChip
              label="Severity"
              value={filters.severity}
              active
              onClear={() => updateFilter("severity", "")}
            />
          )}
          {filters.host_id && (
            <FilterChip
              label="Host"
              value={hosts.find((h) => h.id === filters.host_id)?.name ?? filters.host_id}
              active
              onClear={() => updateFilter("host_id", "")}
            />
          )}
          {filters.event_type && (
            <FilterChip
              label="Type"
              value={filters.event_type}
              active
              onClear={() => updateFilter("event_type", "")}
            />
          )}
          {filters.source_ip && (
            <FilterChip
              label="Source IP"
              value={filters.source_ip}
              active
              onClear={() => updateFilter("source_ip", "")}
            />
          )}
          {filters.username && (
            <FilterChip
              label="User"
              value={filters.username}
              active
              onClear={() => updateFilter("username", "")}
            />
          )}
        </FilterGroup>
      </div>
    </div>
  );
}

export const EventFiltersBar = memo(EventFiltersBarInner);
