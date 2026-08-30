"use client";

import { memo } from "react";
import { SearchBar } from "@/components/design-system/SearchBar";
import { Select } from "@/components/design-system/Select";
import { Button } from "@/components/design-system/Button";
import { TIMELINE_SEVERITIES, TIMELINE_STATUSES } from "@/lib/types/timeline";
import type { TimelineFilters } from "@/lib/types/timeline";

interface TimelineFiltersBarProps {
  filters: TimelineFilters;
  onFiltersChange: (filters: TimelineFilters) => void;
  total: number;
}

function TimelineFiltersBarInner({ filters, onFiltersChange, total }: TimelineFiltersBarProps) {
  const updateFilter = (key: keyof TimelineFilters, value: string) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const activeCount = [filters.severity, filters.status, filters.search].filter(Boolean).length;

  return (
    <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
      <SearchBar
        placeholder="Search timelines..."
        value={filters.search}
        onChange={(v) => updateFilter("search", v)}
        className="flex-1 min-w-0"
      />
      <div className="flex gap-2 items-center flex-wrap">
        <Select
          value={filters.severity}
          onChange={(e) => updateFilter("severity", e.target.value)}
          className="!w-auto !text-xs min-w-[110px]"
          aria-label="Filter by severity"
        >
          <option value="">All severity</option>
          {TIMELINE_SEVERITIES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </Select>
        <Select
          value={filters.status}
          onChange={(e) => updateFilter("status", e.target.value)}
          className="!w-auto !text-xs min-w-[110px]"
          aria-label="Filter by status"
        >
          <option value="">All status</option>
          {TIMELINE_STATUSES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </Select>
        {activeCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onFiltersChange({ host_id: "", severity: "", status: "", search: "" })}
            className="text-xs"
          >
            Clear ({activeCount})
          </Button>
        )}
        <span className="text-xs text-muted tabular-nums whitespace-nowrap">
          {total} timeline{total !== 1 ? "s" : ""}
        </span>
      </div>
    </div>
  );
}

export const TimelineFiltersBar = memo(TimelineFiltersBarInner);
