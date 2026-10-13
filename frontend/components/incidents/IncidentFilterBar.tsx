"use client";

import { useCallback, useMemo } from "react";
import { X } from "lucide-react";
import { SearchBar } from "@/components/design-system/SearchBar";
import { FilterChip, FilterGroup } from "@/components/design-system/FilterChip";
import { Select } from "@/components/design-system/Select";
import { Button } from "@/components/design-system/Button";
import { Badge } from "@/components/design-system/Badge";
import type { IncidentFilters } from "@/lib/types/incident";
import { INCIDENT_SORT_OPTIONS } from "@/lib/types/incident";

interface IncidentFilterBarProps {
  filters: IncidentFilters;
  sort: string;
  severityOptions: Array<{ value: string; label: string }>;
  statusOptions: Array<{ value: string; label: string }>;
  hosts: Array<{ id: string; name: string }>;
  onFilterChange: (filters: IncidentFilters) => void;
  onSortChange: (sort: string) => void;
  onResetPage: () => void;
}

export function IncidentFilterBar({
  filters,
  sort,
  severityOptions,
  statusOptions,
  hosts,
  onFilterChange,
  onSortChange,
  onResetPage,
}: IncidentFilterBarProps) {
  const activeCount = useMemo(() => {
    let count = 0;
    if (filters.severity) count++;
    if (filters.status) count++;
    if (filters.host_id) count++;
    if (filters.q) count++;
    return count;
  }, [filters]);

  const handleSearch = useCallback(
    (q: string) => {
      onFilterChange({ ...filters, q });
      onResetPage();
    },
    [filters, onFilterChange, onResetPage],
  );

  const handleSeverity = useCallback(
    (severity: string) => {
      const next = filters.severity === severity ? "" : severity;
      onFilterChange({ ...filters, severity: next });
      onResetPage();
    },
    [filters, onFilterChange, onResetPage],
  );

  const handleStatus = useCallback(
    (status: string) => {
      const next = filters.status === status ? "" : status;
      onFilterChange({ ...filters, status: next });
      onResetPage();
    },
    [filters, onFilterChange, onResetPage],
  );

  const handleHostChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onFilterChange({ ...filters, host_id: e.target.value });
      onResetPage();
    },
    [filters, onFilterChange, onResetPage],
  );

  const handleSortChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onSortChange(e.target.value);
      onResetPage();
    },
    [onSortChange, onResetPage],
  );

  const handleClearAll = useCallback(() => {
    onFilterChange({
      severity: "",
      status: "",
      host_id: "",
      q: "",
    });
    onResetPage();
  }, [onFilterChange, onResetPage]);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[200px]">
          <SearchBar
            placeholder="Search incidents\u2026"
            value={filters.q}
            onChange={handleSearch}
            size="sm"
          />
        </div>

        <div className="relative">
          <Select
            value={sort}
            onChange={handleSortChange}
            className="!py-1.5 !text-xs !pr-8"
            aria-label="Sort incidents"
          >
            {INCIDENT_SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
        </div>

        <div className="relative">
          <Select
            value={filters.host_id}
            onChange={handleHostChange}
            className="!py-1.5 !text-xs !pr-8"
            aria-label="Filter by host"
          >
            <option value="">All hosts</option>
            {hosts.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {activeCount > 0 && (
        <div className="flex items-center gap-2">
          <Badge variant="status" status="active" className="text-[10px]">
            {activeCount} active
          </Badge>
          <Button
            variant="ghost"
            size="xs"
            onClick={handleClearAll}              icon={<X className="w-3.5 h-3.5" />}
          >
            Clear all
          </Button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4">
        <FilterGroup label="Severity">
          {severityOptions.map((opt) => (
            <FilterChip
              key={opt.value}
              label={opt.label}
              active={filters.severity === opt.value}
              onClick={() => handleSeverity(opt.value)}
              onClear={() => handleSeverity(opt.value)}
            />
          ))}
        </FilterGroup>

        <FilterGroup label="Status">
          {statusOptions.map((opt) => (
            <FilterChip
              key={opt.value}
              label={opt.label}
              active={filters.status === opt.value}
              onClick={() => handleStatus(opt.value)}
              onClear={() => handleStatus(opt.value)}
            />
          ))}
        </FilterGroup>
      </div>
    </div>
  );
}