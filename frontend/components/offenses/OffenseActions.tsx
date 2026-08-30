"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/design-system/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { useOffenseStatusMutation, useOffensePromoteMutation } from "@/lib/hooks/useOffenses";
import { OFFENSE_STATUSES } from "@/lib/types/offense";
import type { OffenseStatus } from "@/lib/types/offense";
import { useRouter } from "next/navigation";

interface Props {
  offenseId: string;
  currentStatus: OffenseStatus;
  incidentId: string | null;
  onStatusChange?: () => void;
}

export function OffenseActions({ offenseId, currentStatus, incidentId, onStatusChange }: Props) {
  const router = useRouter();
  const { toast } = useToast();
  const [confirmStatus, setConfirmStatus] = useState<OffenseStatus | null>(null);

  const statusMutation = useOffenseStatusMutation({
    onSuccess: () => {
      toast("success", "Offense status updated");
      onStatusChange?.();
    },
    onError: (e) => toast("error", "Update failed", e.message),
  });

  const promoteMutation = useOffensePromoteMutation({
    onSuccess: (data) => {
      toast("success", data.created ? "Incident created" : "Linked to existing incident");
      router.push(`/incidents/${data.incident_id}`);
    },
    onError: (e) => toast("error", "Promotion failed", e.message),
  });

  const handleStatus = useCallback((status: OffenseStatus) => {
    setConfirmStatus(status);
  }, []);

  const confirmAction = useCallback(() => {
    if (confirmStatus) {
      statusMutation.mutate({ id: offenseId, status: confirmStatus });
    }
    setConfirmStatus(null);
  }, [confirmStatus, offenseId, statusMutation]);

  const nextStatuses = OFFENSE_STATUSES.filter((s) => s !== currentStatus);

  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <h3 className="text-sm font-semibold mb-3">Analyst Actions</h3>
      <div className="flex flex-wrap gap-2">
        {nextStatuses.map((s) => (
          <Button
            key={s}
            variant={s === "resolved" ? "ghost" : "secondary"}
            size="sm"
            loading={statusMutation.isPending}
            onClick={() => handleStatus(s)}
          >
            {s === "open" ? "Reopen" : s === "investigating" ? "Investigate" : "Resolve"}
          </Button>
        ))}

        {!incidentId && (
          <Button
            variant="primary"
            size="sm"
            loading={promoteMutation.isPending}
            onClick={() => promoteMutation.mutate(offenseId)}
          >
            Create Incident
          </Button>
        )}
      </div>

      <Dialog
        open={!!confirmStatus}
        onClose={() => setConfirmStatus(null)}
        title={`${confirmStatus === "resolved" ? "Resolve" : confirmStatus === "open" ? "Reopen" : "Investigate"} offense?`}
        description={`This will change the offense status to "${confirmStatus}".`}
      >
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="ghost" size="sm" onClick={() => setConfirmStatus(null)}>
            Cancel
          </Button>
          <Button variant="primary" size="sm" onClick={confirmAction}>
            Confirm
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
