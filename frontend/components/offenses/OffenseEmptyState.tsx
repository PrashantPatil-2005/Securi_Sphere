"use client";

import { ShieldAlert, Search } from "lucide-react";
import { EmptyState } from "@/components/design-system/EmptyState";

interface Props {
  hasFilters: boolean;
  onClear: () => void;
}

export function OffenseEmptyState({ hasFilters, onClear }: Props) {
  if (hasFilters) {
    return (
      <EmptyState
        icon={<Search className="w-10 h-10" />}
        title="No matching offenses"
        description="Try adjusting your filters or search terms."
        actionLabel="Clear filters"
        onAction={onClear}
      />
    );
  }

  return (
    <EmptyState
      icon={<ShieldAlert className="w-10 h-10" />}
      title="No offenses"
      description="Offenses are created when correlation rules group related alerts. Try running a simulation."
      action="/simulation"
      actionLabel="Run simulation"
    />
  );
}
