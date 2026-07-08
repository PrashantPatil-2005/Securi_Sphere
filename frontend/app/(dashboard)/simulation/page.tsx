"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { useUser, canPurgeSimulation } from "@/lib/hooks/useUser";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/Panel";
import { useToast } from "@/components/ui/Toast";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { AttackLabHeader } from "@/components/attack-lab/AttackLabHeader";
import { AttackLabTabs } from "@/components/attack-lab/AttackLabTabs";
import { SimulationRunner } from "@/components/attack-lab/SimulationRunner";
import { SimulationLiveProgress } from "@/components/attack-lab/SimulationLiveProgress";
import { CustomEventBuilder } from "@/components/attack-lab/CustomEventBuilder";
import { KillChainPreview } from "@/components/attack-lab/KillChainPreview";
import { InvestigationGuide } from "@/components/attack-lab/InvestigationGuide";
import { SimulationResults } from "@/components/attack-lab/SimulationResults";
import { SimulationFeed } from "@/components/attack-lab/SimulationFeed";
import {
  SimulationRunHistory,
  fetchSimulationRunDetail,
} from "@/components/attack-lab/SimulationRunHistory";
import type {
  AttackLabTab,
  CustomSimulationRequest,
  CustomStepDraft,
  ScenariosResponse,
  SimulationRunResult,
} from "@/lib/types/simulation";
import { track } from "@/lib/telemetry";

function detailToResult(detail: Awaited<ReturnType<typeof fetchSimulationRunDetail>>): SimulationRunResult {
  return {
    message: `Simulation ${detail.scenario_id} completed`,
    events: detail.event_count,
    run_id: detail.id,
    host_id: detail.host_id,
    scenario: detail.scenario_id,
    name: detail.name,
    event_ids: detail.event_ids,
    alert_ids: detail.alert_ids,
    timeline_ids: detail.timeline_ids,
    offense_ids: detail.offense_ids,
  };
}

export default function SimulationPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: user } = useUser();
  const { data: hosts = [], isLoading: hostsLoading } = useHostsList();
  const [tab, setTab] = useState<AttackLabTab>("presets");
  const [hostId, setHostId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [lastResult, setLastResult] = useState<SimulationRunResult | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [purgeConfirmOpen, setPurgeConfirmOpen] = useState(false);

  const { data: scenariosData, isLoading: scenariosLoading, isError, refetch } = useQuery({
    queryKey: ["simulation", "scenarios"],
    queryFn: () => api<ScenariosResponse>("/api/v1/simulation/scenarios"),
    retry: false,
  });

  const scenarios = useMemo(() => scenariosData?.scenarios ?? [], [scenariosData?.scenarios]);
  const enabled = scenariosData?.enabled ?? false;
  const selectedScenario = scenarios.find((s) => s.id === scenarioId) ?? null;
  const showPurge = canPurgeSimulation(user?.role?.name);

  useEffect(() => {
    if (!hostId && hosts[0]) setHostId(hosts[0].id);
  }, [hosts, hostId]);

  useEffect(() => {
    if (!scenarioId && scenarios.length > 0) {
      const preferred = scenarios.find((s) => s.id === "multi_stage_attack") ?? scenarios[0];
      setScenarioId(preferred.id);
    }
  }, [scenarios, scenarioId]);

  const invalidateAfterRun = () => {
    queryClient.invalidateQueries({ queryKey: ["alerts"] });
    queryClient.invalidateQueries({ queryKey: ["events"] });
    queryClient.invalidateQueries({ queryKey: ["offenses"] });
    queryClient.invalidateQueries({ queryKey: ["siem"] });
    queryClient.invalidateQueries({ queryKey: ["timelines"] });
    queryClient.invalidateQueries({ queryKey: ["simulation", "runs"] });
    queryClient.invalidateQueries({ queryKey: ["simulation", "runs", "count"] });
  };

  const runMutation = useMutation({
    mutationFn: () =>
      api<SimulationRunResult>(
        `/api/v1/simulation/run/${scenarioId}?host_id=${hostId}`,
        { method: "POST" },
      ),
    onSuccess: (r) => {
      setLastResult(r);
      setSelectedRunId(r.run_id);
      invalidateAfterRun();
      track("simulation_completed", { scenario_id: r.scenario, events: r.events, run_id: r.run_id });
      toast("success", `${r.message} (${r.events} events)`);
    },
    onError: (e: Error) => toast("error", "Simulation failed", e.message),
  });

  const customRunMutation = useMutation({
    mutationFn: (payload: { host_id: string; name: string; steps: CustomStepDraft[] }) => {
      const body: CustomSimulationRequest = {
        host_id: payload.host_id,
        name: payload.name,
        steps: payload.steps.map((s) => ({
          event_type: s.event_type,
          offset_seconds: s.offset_seconds,
          severity: s.severity,
        })),
      };
      return api<SimulationRunResult>("/api/v1/simulation/custom", {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
    onSuccess: (r) => {
      setLastResult(r);
      setSelectedRunId(r.run_id);
      invalidateAfterRun();
      toast("success", `${r.name} — ${r.events} events injected`);
    },
    onError: (e: Error) => toast("error", "Custom simulation failed", e.message),
  });

  const purgeMutation = useMutation({
    mutationFn: () =>
      api<{ message: string; events_deleted: number }>("/api/v1/simulation/purge", { method: "DELETE" }),
    onSuccess: (r) => {
      setLastResult(null);
      setSelectedRunId(null);
      queryClient.invalidateQueries();
      toast("success", r.message, `${r.events_deleted} simulated events removed`);
    },
    onError: (e: Error) => toast("error", "Purge failed", e.message),
  });

  const handlePurge = () => setPurgeConfirmOpen(true);

  const handleHistorySelect = async (runId: string) => {
    setSelectedRunId(runId);
    try {
      const detail = await fetchSimulationRunDetail(runId);
      setLastResult(detailToResult(detail));
    } catch (e) {
      toast("error", "Failed to load run", e instanceof Error ? e.message : "Unknown error");
    }
  };

  const loading = hostsLoading || scenariosLoading;
  const running = runMutation.isPending || customRunMutation.isPending;

  return (
    <div className="space-y-6">
      <AttackLabHeader
        enabled={enabled}
        showPurge={showPurge}
        onPurge={handlePurge}
        purgePending={purgeMutation.isPending}
      />

      {loading ? (
        <TableSkeleton rows={6} />
      ) : isError ? (
        <QueryError onRetry={() => refetch()} />
      ) : scenarios.length === 0 ? (
        <EmptyState
          title="Attack Lab unavailable"
          description="Admin or analyst access required, or simulation disabled in this environment."
        />
      ) : (
        <>
          <AttackLabTabs active={tab} onChange={setTab} />

          <div className="grid lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,1fr)] gap-6">
            <div className="space-y-6">
              {tab === "presets" && (
                <>
                  <SimulationLiveProgress running={running} scenarioName={selectedScenario?.name} />
                  <SimulationRunner
                    hosts={hosts}
                    scenarios={scenarios}
                    hostId={hostId}
                    scenarioId={scenarioId}
                    enabled={enabled}
                    running={running}
                    onHostChange={setHostId}
                    onScenarioChange={setScenarioId}
                    onRun={() => runMutation.mutate()}
                  />
                  <KillChainPreview scenario={selectedScenario} />
                </>
              )}

              {tab === "custom" && (
                <CustomEventBuilder
                  hosts={hosts}
                  hostId={hostId}
                  enabled={enabled}
                  running={running}
                  selectedPreset={selectedScenario}
                  onHostChange={setHostId}
                  onRun={(payload) => customRunMutation.mutateAsync(payload)}
                />
              )}

              {tab === "history" && (
                <SimulationRunHistory
                  selectedRunId={selectedRunId}
                  onSelect={handleHistorySelect}
                />
              )}
            </div>

            <InvestigationGuide />
          </div>

          <SimulationResults
            result={lastResult}
            onRunAgain={() => {
              setLastResult(null);
              setSelectedRunId(null);
            }}
          />

          <SimulationFeed running={running} />
        </>
      )}

      <ConfirmDialog
        open={purgeConfirmOpen}
        onClose={() => setPurgeConfirmOpen(false)}
        onConfirm={() => {
          purgeMutation.mutate();
          setPurgeConfirmOpen(false);
        }}
        title="Purge simulation data"
        description="Remove all simulated events, timelines, open alerts, and run history? This cannot be undone."
        confirmLabel="Purge all"
        danger
        loading={purgeMutation.isPending}
      />
    </div>
  );
}
