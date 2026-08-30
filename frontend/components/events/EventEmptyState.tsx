"use client";

import { memo } from "react";
import { Activity } from "lucide-react";
import { EmptyState } from "@/components/design-system/EmptyState";

interface EventEmptyStateProps {
  hasFilters: boolean;
  onClear: () => void;
}

function EventEmptyStateInner({ hasFilters, onClear }: EventEmptyStateProps) {
  if (hasFilters) {
    return (
      <EmptyState
        title="No matching events"
        description="Try adjusting your filters or time range."
        icon={<Activity className="w-10 h-10 opacity-40" />}
        actionLabel="Clear filters"
        onAction={onClear}
      />
    );
  }

  return (
    <EmptyState
      title="No events"
      description="Enroll an agent on a host to start collecting security telemetry."
      icon={<Activity className="w-10 h-10 opacity-40" />}
      action="/hosts"
      actionLabel="Add a host"
    />
  );
}

export const EventEmptyState = memo(EventEmptyStateInner);
