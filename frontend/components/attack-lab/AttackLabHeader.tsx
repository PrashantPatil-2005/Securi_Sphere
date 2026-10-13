"use client";

import { PageHeader } from "@/components/ui/Panel";
import { HelpTooltip } from "@/components/ui/HelpTooltip";
import { AlertTriangle } from "lucide-react";
import { useSimulationMode } from "@/lib/hooks/useSimulationMode";
import { Badge } from "@/components/design-system/Badge";

interface Props {
  enabled: boolean;
}

export function AttackLabHeader({ enabled }: Props) {
  const { mode, hostInfo } = useSimulationMode();

  return (
    <div className="space-y-4">
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2">
            Attack Simulation Lab
            <HelpTooltip content="Generate realistic attack events on an enrolled host. Run a scenario, then follow the investigation guide to triage alerts and offenses." />
          </span>
        }
        subtitle={mode === "live"
          ? `Live Linux Lab — ${hostInfo?.hostName || ''} — ${hostInfo?.agentOnline ? 'Agent online' : 'Agent offline'}`
          : mode === "replay"
            ? "Event Replay — Sanitized event sequences with controlled time progression"
            : mode === "presets"
              ? "Guided Synthetic Simulation — Exercise real normalization, detection, correlation, and alert-building logic"
              : "Attack Simulation Lab"
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
      {mode && mode !== "presets" && (
        <Badge className="ms-2">
          {mode === "live" ? "LIVE" : mode === "replay" ? "REPLAYED" : "SYNTHETIC"}
        </Badge>
      )}
    </div>
  );
}
