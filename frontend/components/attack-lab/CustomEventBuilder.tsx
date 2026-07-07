"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FlaskConical, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/Panel";
import { SimulationStepEditor } from "./SimulationStepEditor";
import { KillChainPreview } from "./KillChainPreview";
import type {
  CustomStepDraft,
  EventTypesResponse,
  Scenario,
  SimulationRunResult,
} from "@/lib/types/simulation";

interface HostOption {
  id: string;
  name: string;
}

interface Props {
  hosts: HostOption[];
  hostId: string;
  enabled: boolean;
  running: boolean;
  selectedPreset: Scenario | null;
  onHostChange: (id: string) => void;
  onRun: (payload: { host_id: string; name: string; steps: CustomStepDraft[] }) => Promise<SimulationRunResult>;
}

function newStep(eventType: string): CustomStepDraft {
  return {
    id: crypto.randomUUID(),
    event_type: eventType,
    offset_seconds: 0,
    severity: "medium",
  };
}

function stepsFromPreset(preset: Scenario): CustomStepDraft[] {
  return preset.steps.map((s) => ({
    id: crypto.randomUUID(),
    event_type: s.event_type,
    offset_seconds: s.offset_seconds,
    severity: s.event_type.includes("failure") ? "medium" : "high",
  }));
}

export function CustomEventBuilder({
  hosts,
  hostId,
  enabled,
  running,
  selectedPreset,
  onHostChange,
  onRun,
}: Props) {
  const { data: eventTypesData } = useQuery({
    queryKey: ["simulation", "event-types"],
    queryFn: () => api<EventTypesResponse>("/api/v1/simulation/event-types"),
  });

  const eventTypes = eventTypesData?.event_types ?? [];
  const defaultType = eventTypes[0]?.event_type ?? "ssh_login_failure";

  const [name, setName] = useState("Custom attack chain");
  const [steps, setSteps] = useState<CustomStepDraft[]>(() => [newStep(defaultType)]);

  useEffect(() => {
    if (eventTypes.length && steps.length === 1 && steps[0].event_type === "ssh_login_failure") {
      setSteps([newStep(eventTypes[0].event_type)]);
    }
  }, [eventTypes]); // eslint-disable-line react-hooks/exhaustive-deps

  const previewScenario: Scenario | null =
    steps.length > 0
      ? {
          id: "custom",
          name: name,
          summary: "Custom event chain",
          difficulty: "custom",
          event_count: steps.length,
          duration_seconds: Math.max(...steps.map((s) => s.offset_seconds), 0),
          steps: steps.map((s, i) => ({
            order: i + 1,
            event_type: s.event_type,
            offset_seconds: s.offset_seconds,
            description: null,
            mitre: null,
          })),
          expected_alerts: [],
          expected_outcomes: [],
        }
      : null;

  const loadFromPreset = () => {
    if (!selectedPreset) return;
    setName(`${selectedPreset.name} (custom)`);
    setSteps(stepsFromPreset(selectedPreset));
  };

  const handleRun = async () => {
    try {
      await onRun({
        host_id: hostId,
        name,
        steps,
      });
    } catch {
      // Parent mutation shows toast
    }
  };

  if (hosts.length === 0) {
    return (
      <EmptyState
        title="No hosts available"
        description="Add and enroll a host before running custom simulations."
        action="/hosts"
        actionLabel="Go to Hosts"
      />
    );
  }

  return (
    <div className="space-y-4">
      <GlassPanel className="space-y-4">
        <label htmlFor="custom-host" className="text-subheading block">
          Target host
        </label>
        <select
          id="custom-host"
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

        <label htmlFor="custom-name" className="text-subheading block">
          Simulation name
        </label>
        <input
          id="custom-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input-siem w-full"
          maxLength={255}
        />

        <div className="flex items-center justify-between gap-2">
          <h2 className="text-subheading">Event steps</h2>
          <div className="flex gap-2">
            {selectedPreset && (
              <Button type="button" variant="ghost" size="sm" onClick={loadFromPreset}>
                Load from preset
              </Button>
            )}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={steps.length >= 20}
              onClick={() => setSteps((prev) => [...prev, newStep(defaultType)])}
            >
              <Plus className="w-4 h-4" />
              Add step
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          {steps.map((step, index) => (
            <SimulationStepEditor
              key={step.id}
              step={step}
              index={index}
              total={steps.length}
              eventTypes={eventTypes}
              onChange={(updated) =>
                setSteps((prev) => prev.map((s) => (s.id === step.id ? updated : s)))
              }
              onRemove={() => setSteps((prev) => prev.filter((s) => s.id !== step.id))}
              onMoveUp={() =>
                setSteps((prev) => {
                  if (index === 0) return prev;
                  const next = [...prev];
                  [next[index - 1], next[index]] = [next[index], next[index - 1]];
                  return next;
                })
              }
              onMoveDown={() =>
                setSteps((prev) => {
                  if (index >= prev.length - 1) return prev;
                  const next = [...prev];
                  [next[index], next[index + 1]] = [next[index + 1], next[index]];
                  return next;
                })
              }
            />
          ))}
        </div>

        {steps.length >= 20 && (
          <p className="text-xs text-warning">Maximum 20 steps per custom simulation.</p>
        )}

        <Button
          type="button"
          disabled={!hostId || !name.trim() || steps.length === 0 || !enabled || running}
          loading={running}
          onClick={handleRun}
        >
          <FlaskConical className="w-4 h-4" />
          Run custom simulation
        </Button>
      </GlassPanel>

      <KillChainPreview scenario={previewScenario} />
    </div>
  );
}
