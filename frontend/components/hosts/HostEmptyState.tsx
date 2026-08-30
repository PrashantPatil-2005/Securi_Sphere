"use client";

import { memo } from "react";
import { Server } from "lucide-react";
import { EmptyState } from "@/components/design-system/EmptyState";

interface HostEmptyStateProps {
  hasFilters: boolean;
  onClear: () => void;
}

function HostEmptyStateInner({ hasFilters, onClear }: HostEmptyStateProps) {
  if (hasFilters) {
    return (
      <EmptyState
        title="No matching hosts"
        description="Try adjusting your filters or search terms."
        icon={<Server className="w-10 h-10 opacity-40" />}
        actionLabel="Clear filters"
        onAction={onClear}
      />
    );
  }

  return (
    <EmptyState
      title="No hosts"
      description="Add a host to get started, then enroll a Debian or Ubuntu VM with the install command."
      icon={<Server className="w-10 h-10 opacity-40" />}
    />
  );
}

export const HostEmptyState = memo(HostEmptyStateInner);
