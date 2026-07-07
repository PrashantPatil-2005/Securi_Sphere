"use client";

import { FlaskConical } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Panel";
import { ScenarioCard } from "./ScenarioCard";
import type { Scenario } from "@/lib/types/simulation";

interface HostOption {
  id: string;
  name: string;
}

interface Props {
  hosts: HostOption[];
  scenarios: Scenario[];
  hostId: string;
  scenarioId: string;
  enabled: boolean;
  running: boolean;
  onHostChange: (id: string) => void;
  onScenarioChange: (id: string) => void;
  onRun: () => void;
}

export function SimulationRunner({
  hosts,
  scenarios,
  hostId,
  scenarioId,
  enabled,
  running,
  onHostChange,
  onScenarioChange,
  onRun,
}: Props) {
  if (hosts.length === 0) {
    return (
      <EmptyState
        title="No hosts available"
        description="Add and enroll a host before running attack simulations."
        action="/hosts"
        actionLabel="Go to Hosts"
      />
    );
  }

  return (
    <div className="space-y-4">
      <GlassPanel>
        <label htmlFor="attack-lab-host" className="text-subheading block mb-2">
          Target host
        </label>
        <select
          id="attack-lab-host"
          value={hostId}
          onChange={(e) => onHostChange(e.target.value)}
          className="input-siem w-full"
        >
          {hosts.map((h) => (
            <option key={h.id} value={h.id}>
              {h.name}
            </option>
          ))}
        </select>
      </GlassPanel>

      <div>
        <h2 className="text-subheading mb-3">Attack scenario</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {scenarios.map((s) => (
            <ScenarioCard
              key={s.id}
              scenario={s}
              selected={scenarioId === s.id}
              onSelect={() => onScenarioChange(s.id)}
            />
          ))}
        </div>
      </div>

      <Button
        type="button"
        disabled={!hostId || !scenarioId || !enabled || running}
        loading={running}
        onClick={onRun}
        className="w-full sm:w-auto"
      >
        <FlaskConical className="w-4 h-4" />
        Run simulation
      </Button>
    </div>
  );
}
