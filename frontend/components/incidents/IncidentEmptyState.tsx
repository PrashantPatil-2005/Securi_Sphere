"use client";

import { ClipboardList, Search } from "lucide-react";
import { EmptyState } from "@/components/design-system/EmptyState";

interface Props {
  hasFilters: boolean;
  onClear: () => void;
}

export function IncidentEmptyState({ hasFilters, onClear }: Props) {
  if (hasFilters) {
    return (
      <EmptyState
        icon={<Search className="w-10 h-10" />}
        title="No matching incidents"
        description="Try adjusting your filters."
        actionLabel="Clear filters"
        onAction={onClear}
      />
    );
  }

  return (
    <EmptyState
      icon={<ClipboardList className="w-10 h-10" />}
      title="No incidents"
      description="Create an incident to begin tracking a security investigation."
    />
  );
}
