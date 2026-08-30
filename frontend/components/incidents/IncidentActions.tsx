"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/design-system/Button";
import { Dialog } from "@/components/ui/Dialog";
import { useToast } from "@/components/ui/Toast";
import { useIncidentStatusMutation } from "@/lib/hooks/useIncidents";
import { INCIDENT_STATUS_TRANSITIONS } from "@/lib/types/incident";
import type { IncidentStatus } from "@/lib/types/incident";

interface Props {
  incidentId: string;
  currentStatus: IncidentStatus;
  onStatusChange?: () => void;
}

export function IncidentActions({ incidentId, currentStatus, onStatusChange }: Props) {
  const { toast } = useToast();
  const [confirmStatus, setConfirmStatus] = useState<IncidentStatus | null>(null);

  const statusMutation = useIncidentStatusMutation({
    onSuccess: () => {
      toast("success", "Incident status updated");
      onStatusChange?.();
    },
    onError: (e) => toast("error", "Update failed", e.message),
  });

  const allowedTransitions = INCIDENT_STATUS_TRANSITIONS[currentStatus] ?? [];

  const handleStatus = useCallback((status: IncidentStatus) => {
    setConfirmStatus(status);
  }, []);

  const confirmAction = useCallback(() => {
    if (confirmStatus) {
      statusMutation.mutate({ id: incidentId, status: confirmStatus });
    }
    setConfirmStatus(null);
  }, [confirmStatus, incidentId, statusMutation]);

  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <h3 className="text-sm font-semibold mb-3">Status</h3>
      <div className="flex flex-wrap gap-2">
        {allowedTransitions.map((s) => (
          <Button
            key={s}
            variant={s === "resolved" || s === "closed" ? "ghost" : "secondary"}
            size="sm"
            loading={statusMutation.isPending}
            onClick={() => handleStatus(s)}
          >
            {s === "open" ? "Reopen" : s === "investigating" ? "Investigate" : s === "resolved" ? "Resolve" : "Close"}
          </Button>
        ))}
      </div>

      <Dialog
        open={!!confirmStatus}
        onClose={() => setConfirmStatus(null)}
        title={`${confirmStatus === "resolved" ? "Resolve" : confirmStatus === "closed" ? "Close" : confirmStatus === "open" ? "Reopen" : "Investigate"} incident?`}
        description={`This will change the incident status to "${confirmStatus}".`}
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
