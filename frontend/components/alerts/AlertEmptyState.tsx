"use client";

import { ShieldAlert, Filter } from "lucide-react";
import { EmptyState } from "@/components/design-system/EmptyState";

interface AlertEmptyStateProps {
  hasFilters: boolean;
}

export function AlertEmptyState({ hasFilters }: AlertEmptyStateProps) {
  if (hasFilters) {
    return (
      <EmptyState
        title="No alerts match your filters"
        description="Try adjusting your search or clearing some filters to see more results."
        icon={<Filter className="w-7 h-7" />}
      />
    );
  }

  return (
    <EmptyState
      title="No alerts yet"
      description="When the simulator generates alerts, they will appear here. Run a simulation to see your first alert."
      icon={<ShieldAlert className="w-7 h-7" />}
    />
  );
}
