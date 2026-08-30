"use client";

import { memo, useCallback } from "react";
import { SearchBar } from "@/components/design-system/SearchBar";
import { FilterChip } from "@/components/design-system/FilterChip";
import { FilterGroup } from "@/components/design-system/FilterChip";
import { Select } from "@/components/design-system/Select";
import { Button } from "@/components/design-system/Button";
import { HOST_STATUSES, HOST_SORT_OPTIONS } from "@/lib/types/host";
import type { HostFilters } from "@/lib/types/host";

interface HostFiltersBarProps {
  filters: HostFilters;
  sort: string;
  onFiltersChange: (filters: HostFilters) => void;
  onSortChange: (sort: string) => void;
  total: number;
}

function HostFiltersBarInner({
  filters,
  sort,
  onFiltersChange,
  onSortChange,
  total,
}: HostFiltersBarProps) {
  const updateFilter = useCallback(
    (key: keyof HostFilters, value: string) => {
      onFiltersChange({ ...filters, [key]: value });
    },
    [filters, onFiltersChange],
  );

  const clearAll = useCallback(() => {
    onFiltersChange({
      hostname: "",
      status: "",
      os_info: "",
      min_risk: "",
      max_risk: "",
    });
  }, [onFiltersChange]);

  const activeCount = [filters.hostname, filters.status, filters.os_info, filters.min_risk, filters.max_risk].filter(Boolean).length;

  return (
    <div className="space-y-3">
      {/* Search row */}
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchBar
          placeholder="Search by hostname, IP, or name..."
          value={filters.hostname}
          onChange={(v) => updateFilter("hostname", v)}
          className="flex-1"
        />
        <div className="flex gap-2 items-center">
          <Select
            value={sort}
            onChange={(e) => onSortChange(e.target.value)}
            className="!w-auto !text-xs"
            aria-label="Sort hosts"
          >
            {HOST_SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </Select>
          <span className="text-xs text-muted tabular-nums whitespace-nowrap">
            {total.toLocaleString()} hosts
          </span>
        </div>
      </div>

      {/* Filter chips row */}
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={filters.status}
          onChange={(e) => updateFilter("status", e.target.value)}
          className="!w-auto !text-xs min-w-[120px]"
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          {HOST_STATUSES.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </Select>

        <Select
          value={filters.os_info}
          onChange={(e) => updateFilter("os_info", e.target.value)}
          className="!w-auto !text-xs min-w-[120px]"
          aria-label="Filter by OS"
        >
          <option value="">All OS</option>
          <option value="Linux">Linux</option>
          <option value="Ubuntu">Ubuntu</option>
          <option value="Debian">Debian</option>
        </Select>

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

        <FilterGroup>
          {filters.status && (
            <FilterChip
              label="Status"
              value={filters.status}
              active
              onClear={() => updateFilter("status", "")}
            />
          )}
          {filters.os_info && (
            <FilterChip
              label="OS"
              value={filters.os_info}
              active
              onClear={() => updateFilter("os_info", "")}
            />
          )}
          {filters.min_risk && (
            <FilterChip
              label="Min risk"
              value={filters.min_risk}
              active
              onClear={() => updateFilter("min_risk", "")}
            />
          )}
          {filters.max_risk && (
            <FilterChip
              label="Max risk"
              value={filters.max_risk}
              active
              onClear={() => updateFilter("max_risk", "")}
            />
          )}
        </FilterGroup>
      </div>
    </div>
  );
}

export const HostFiltersBar = memo(HostFiltersBarInner);
