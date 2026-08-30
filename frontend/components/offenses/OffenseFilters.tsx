"use client";

import { SearchBar } from "@/components/design-system/SearchBar";
import { Select } from "@/components/design-system/Select";
import { FilterChip } from "@/components/design-system/FilterChip";
import type { OffenseFilters } from "@/lib/types/offense";
import { OFFENSE_STATUSES } from "@/lib/types/offense";
import { useHostsList } from "@/lib/hooks/useApiQuery";

interface Props {
  filters: OffenseFilters;
  onChange: (f: OffenseFilters) => void;
  total: number;
}

export function OffenseFilterBar({ filters, onChange, total }: Props) {
  const { data: hosts = [] } = useHostsList();
  const activeCount = [filters.status, filters.host_id, filters.q].filter(Boolean).length;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <SearchBar
        value={filters.q ?? ""}
        onChange={(q) => onChange({ ...filters, q: q || undefined })}
        placeholder="Search offenses…"
        className="w-64"
      />

      <div className="flex flex-wrap gap-1">
        {OFFENSE_STATUSES.map((s) => (
          <FilterChip
            key={s}
            label={s.charAt(0).toUpperCase() + s.slice(1)}
            active={filters.status === s}
            onClick={() => onChange({ ...filters, status: filters.status === s ? undefined : s })}
          />
        ))}
      </div>

      {hosts.length > 0 && (
        <Select
          value={filters.host_id ?? ""}
          onChange={(e) => onChange({ ...filters, host_id: e.target.value || undefined })}
          className="w-40"
        >
          <option value="">All hosts</option>
          {hosts.map((h: { id: string; name: string }) => (
            <option key={h.id} value={h.id}>{h.name}</option>
          ))}
        </Select>
      )}

      {activeCount > 0 && (
        <button
          type="button"
          onClick={() => onChange({})}
          className="text-xs text-muted hover:text-foreground transition-colors"
        >
          Clear all ({activeCount})
        </button>
      )}

      <span className="ml-auto text-xs text-muted">
        {total} offense{total !== 1 ? "s" : ""}
      </span>
    </div>
  );
}
