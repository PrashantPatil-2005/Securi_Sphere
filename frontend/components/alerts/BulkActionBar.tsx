"use client";

import { useState } from "react";
import { AlertTriangle, Eye, UserCheck, CheckCircle2, XCircle, X } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Button } from "@/components/design-system/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

interface BulkActionBarProps {
  count: number;
  isPending: boolean;
  onAction: (payload: { status?: string; assigned_to?: string }) => void;
  onClear: () => void;
  onConfirm: (action: string, callback: () => void) => void;
}

export function BulkActionBar({
  count,
  isPending,
  onAction,
  onClear,
}: BulkActionBarProps) {
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);

  const handleConfirmed = (status: string) => {
    onAction({ status });
    setConfirmTarget(null);
  };

  const handleAssign = () => {
    onAction({ status: "investigating", assigned_to: "me" });
  };

  return (
    <>
      <div
        className={cn(
          "fixed bottom-6 left-1/2 -translate-x-1/2 z-40",
          "flex items-center gap-3 px-4 py-2.5 rounded-lg",
          "bg-card-elevated border border-border shadow-lg",
          "animate-slide-up",
        )}
        role="toolbar"
        aria-label="Bulk actions"
      >
        <div className="flex items-center gap-2 pr-3 border-r border-border-subtle">
          <AlertTriangle className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-foreground tabular-nums">
            {count} selected
          </span>
        </div>

        <Button
          variant="ghost"
          size="xs"
          onClick={handleAssign}
          disabled={isPending}
          icon={<UserCheck className="w-3.5 h-3.5" />}
        >
          Assign to me
        </Button>

        <Button
          variant="ghost"
          size="xs"
          onClick={() => onAction({ status: "investigating" })}
          disabled={isPending}
          icon={<Eye className="w-3.5 h-3.5" />}
        >
          Investigate
        </Button>

        <Button
          variant="ghost"
          size="xs"
          onClick={() => setConfirmTarget("resolved")}
          disabled={isPending}
          icon={<CheckCircle2 className="w-3.5 h-3.5" />}
        >
          Resolve
        </Button>

        <Button
          variant="ghost"
          size="xs"
          onClick={() => setConfirmTarget("closed")}
          disabled={isPending}
          icon={<XCircle className="w-3.5 h-3.5" />}
        >
          Close
        </Button>

        <div className="pl-2 border-l border-border-subtle">
          <Button
            variant="ghost"
            size="xs"
            onClick={onClear}
            icon={<X className="w-3.5 h-3.5" />}
          >
            Clear
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmTarget === "resolved"}
        onClose={() => setConfirmTarget(null)}
        onConfirm={() => handleConfirmed("resolved")}
        title="Resolve selected alerts"
        description={`Are you sure you want to resolve ${count} alert${count === 1 ? "" : "s"}?`}
        confirmLabel="Resolve"
        danger={false}
        loading={isPending}
      />

      <ConfirmDialog
        open={confirmTarget === "closed"}
        onClose={() => setConfirmTarget(null)}
        onConfirm={() => handleConfirmed("closed")}
        title="Close selected alerts"
        description={`Are you sure you want to close ${count} alert${count === 1 ? "" : "s"}? This action cannot be undone.`}
        confirmLabel="Close"
        danger
        loading={isPending}
      />
    </>
  );
}
