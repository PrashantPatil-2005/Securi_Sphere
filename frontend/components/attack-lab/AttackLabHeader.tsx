"use client";

import { AlertTriangle } from "lucide-react";
import { PageHeader } from "@/components/ui/Panel";
import { HelpTooltip } from "@/components/ui/HelpTooltip";
import { Button } from "@/components/ui/Button";

interface Props {
  enabled: boolean;
  showPurge: boolean;
  onPurge: () => void;
  purgePending: boolean;
}

export function AttackLabHeader({ enabled, showPurge, onPurge, purgePending }: Props) {
  return (
    <div className="space-y-4">
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2">
            Attack Simulation Lab
            <HelpTooltip content="Generate realistic attack events on an enrolled host. Run a scenario, then follow the investigation guide to triage alerts and offenses." />
          </span>
        }
        subtitle="Inject synthetic events for demos and SOC training. Dashboard charts may hide simulated data by default — purge when done."
        action={
          showPurge ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={purgePending}
              loading={purgePending}
              onClick={onPurge}
            >
              Purge simulated data
            </Button>
          ) : undefined
        }
      />
      {!enabled && (
        <div className="flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 px-4 py-3 text-sm">
          <AlertTriangle className="w-4 h-4 text-warning shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-warning">Simulation disabled</p>
            <p className="text-muted mt-0.5">
              Set <code className="text-xs">ENABLE_SIMULATION=true</code> in the backend environment and restart the server.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
