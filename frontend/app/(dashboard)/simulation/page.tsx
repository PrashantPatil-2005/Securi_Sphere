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
import { LiveAttackBanner } from "@/components/attack-lab/LiveAttackBanner";
import { CustomEventBuilder } from "@/components/attack-lab/CustomEventBuilder";
import { KillChainPreview } from "@/components/attack-lab/KillChainPreview";
import { SimulationResults } from "@/components/attack-lab/SimulationResults";
import { SimulationFeed } from "@/components/attack-lab/SimulationFeed";
import { RawLogTail } from "@/components/attack-lab/RawLogTail";
import { OperationalReadinessPanel } from "@/components/attack-lab/OperationalReadinessPanel";
import {
  SimulationRunHistory,
  fetchSimulationRunDetail,
} from "@/components/attack-lab/SimulationRunHistory";
import type {
  CustomSimulationRequest,
  CustomStepDraft,
  ScenariosResponse,
  SimulationRunResetResult,
  SimulationRunResult,
} from "@/lib/types/simulation";
import { useSimulationMode } from "@/lib/hooks/useSimulationMode";
import { track } from "@/lib/telemetry";
import {
  disableSimulationDashboardSession,
  enableSimulationDashboardSession,
} from "@/lib/simulation-session";

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
    incident_ids: detail.incident_ids ?? [],
    alerts: detail.alerts ?? [],
    expected_alerts: detail.expected_alerts ?? [],
  };
}

export default function SimulationPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: user } = useUser();
  const { data: hosts = [], isLoading: hostsLoading } = useHostsList();
  const [hostId, setHostId] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [lastResult, setLastResult] = useState<SimulationRunResult | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [purgeConfirmOpen, setPurgeConfirmOpen] = useState(false);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);
  const [expectedEvents, setExpectedEvents] = useState<number | undefined>(undefined);

  const { mode, setMode, hostInfo } = useSimulationMode();

  const { data: scenariosData, isLoading: scenariosLoading, isError, refetch } = useQuery({
    queryKey: ["simulation", "scenarios"],
    queryFn: () => api<ScenariosResponse>("/api/v1/simulation/scenarios"),
    retry: false,
  });

  const scenarios = useMemo(() => scenariosData?.scenarios ?? [], [scenariosData?.scenarios]);
  const enabled = scenariosData?.enabled ?? false;
  const selectedScenario = scenarios.find((s) => s.id === scenarioId) ?? null;
  const showPurge = canPurgeSimulation(user?.role?.name);
  const activeHostName =
    hosts.find((h) => h.id === hostId)?.name ?? hostInfo?.hostName ?? "Attack Lab";

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
        `/api/v1/simulation/run/${scenarioId}?host_id=${hostId}&pace=stream`,
        { method: "POST" },
      ),
    onMutate: () => {
      setRunStartedAt(Date.now());
      setExpectedEvents(selectedScenario?.steps.length);
    },
    onSuccess: (r) => {
      enableSimulationDashboardSession();
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
        pace: "stream",
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
    onMutate: (payload) => {
      setRunStartedAt(Date.now());
      setExpectedEvents(payload.steps.length);
    },
    onSuccess: (r) => {
      enableSimulationDashboardSession();
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
      disableSimulationDashboardSession();
      setLastResult(null);
      setSelectedRunId(null);
      setRunStartedAt(null);
      setExpectedEvents(undefined);
      invalidateAfterRun();
      queryClient.invalidateQueries({ queryKey: ["simulation"] });
      toast("success", r.message, `${r.events_deleted} simulated events removed`);
    },
    onError: (e: Error) => toast("error", "Purge failed", e.message),
  });

  const replayMutation = useMutation({
    mutationFn: (runId: string) =>
      api<SimulationRunResult>(`/api/v1/simulation/runs/${runId}/replay`, { method: "POST" }),
    onMutate: () => {
      setRunStartedAt(Date.now());
    },
    onSuccess: (r) => {
      enableSimulationDashboardSession();
      setLastResult(r);
      setSelectedRunId(r.run_id);
      setExpectedEvents(scenarios.find((s) => s.id === r.scenario)?.steps.length);
      invalidateAfterRun();
      track("simulation_completed", { scenario_id: r.scenario, events: r.events, run_id: r.run_id });
      toast("success", `Replayed ${r.name} (${r.events} events)`);
    },
    onError: (e: Error) => toast("error", "Replay failed", e.message),
  });

  const resetMutation = useMutation({
    mutationFn: (runId: string) =>
      api<SimulationRunResetResult>(`/api/v1/simulation/runs/${runId}`, { method: "DELETE" }),
    onSuccess: (r) => {
      if (selectedRunId === r.run_id) {
        setLastResult(null);
        setSelectedRunId(null);
      }
      invalidateAfterRun();
      queryClient.invalidateQueries({ queryKey: ["simulation"] });
      toast("success", r.message, `${r.events_deleted} events · ${r.alerts_deleted} alerts removed`);
    },
    onError: (e: Error) => toast("error", "Reset failed", e.message),
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

  const presetsContent = (
    <>
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
      <OperationalReadinessPanel
        scenarioId={scenarioId || null}
        hostId={hostId || null}
      />
    </>
  );

  const customContent = (
    <CustomEventBuilder
      hosts={hosts}
      hostId={hostId}
      enabled={enabled}
      running={running}
      selectedPreset={selectedScenario}
      onHostChange={setHostId}
      onRun={(payload) => customRunMutation.mutateAsync(payload)}
    />
  );

  const historyContent = (
    <SimulationRunHistory
      selectedRunId={selectedRunId}
      onSelect={handleHistorySelect}
      onReplay={(runId) => replayMutation.mutate(runId)}
      onReset={(runId) => resetMutation.mutate(runId)}
      replayPendingId={replayMutation.isPending ? replayMutation.variables : null}
      resetPendingId={resetMutation.isPending ? resetMutation.variables : null}
      showPurge={showPurge}
      onPurge={handlePurge}
      purgePending={purgeMutation.isPending}
    />
  );

  const liveContent = hostInfo ? (
    <div>
      <div className="grid lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,1fr)] gap-6">
        <div className="space-y-6">
          <h2 className="text-subheading mb-2">Live Linux Lab</h2>
          <p className="text-muted mb-4">Authorized lab host with active agent telemetry</p>
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
        </div>

        <div className="space-y-6">
          <h3 className="text-subheading">Host Status</h3>
          <p className="text-muted mb-2">Host: {hostInfo.hostName}</p>
          <p className="text-muted mb-2">
            Agent: {hostInfo.agentOnline ? "Online" : "Offline"}
          </p>
          <p className="text-muted small">Last seen: {hostInfo.lastSeen || "N/A"}</p>
          <p className="text-muted small">
            {hostInfo.agentOnline
              ? "Agent is sending telemetry"
              : "Agent is offline — use guided synthetic simulation instead"}
          </p>
        </div>
      </div>
    </div>
  ) : (
    <EmptyState
      title="Select a host for Live Linux Lab"
      description="Choose an enrolled host to display agent status, last heartbeat, and live lab instructions."
      action="/hosts"
      actionLabel="Go to Hosts"
    />
  );

  const replayContent = selectedScenario ? (
    <div>
      <h2 className="text-subheading mb-2">Event Replay</h2>
      <p className="text-muted mb-4">
        Controlled replay of sanitized event sequences. Events are marked as REPLAYED and
        will not appear in live metrics.
      </p>
      <div className="glass-panel p-4 rounded-lg border border-border-subtle">
        <p className="text-muted small">
          Scenario: {selectedScenario.name} ({selectedScenario.difficulty})
        </p>
        <p className="text-muted small">
          Expected alerts: {selectedScenario.expected_alerts.join(", ")}
        </p>
        <p className="text-muted small">
          Time progression:{" "}
          {selectedScenario.steps
            .map((s) => `${s.event_type} @ T+${s.offset_seconds}s`)
            .join(", ")}
        </p>
      </div>
    </div>
  ) : (
    <EmptyState
      title="Select a scenario for Event Replay"
      description="Replay sanitized, predefined event sequences with controlled time progression to demonstrate multi-stage attack correlation."
    />
  );

  return (
    <div className="space-y-6">
      <AttackLabHeader enabled={enabled} />

      {enabled && (
        <LiveAttackBanner
          running={running}
          hostId={hostId}
          hostName={activeHostName}
          scenarioName={selectedScenario?.name}
          expectedEvents={expectedEvents}
          runStartedAt={runStartedAt}
        />
      )}

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
          <AttackLabTabs active={mode} onChange={setMode} />

          <SimulationLiveProgress
            running={running}
            scenarioName={selectedScenario?.name}
            hostId={hostId}
            expectedEvents={expectedEvents}
            runStartedAt={runStartedAt}
          />

          <div className="space-y-6">
            {mode === "presets" && presetsContent}
            {mode === "custom" && customContent}
            {mode === "history" && historyContent}
            {mode === "live" && liveContent}
            {mode === "replay" && replayContent}
          </div>
        </>
      )}

      <SimulationResults
        result={lastResult}
        onRunAgain={() => {
          setLastResult(null);
          setSelectedRunId(null);
        }}
        onReplay={lastResult ? () => replayMutation.mutate(lastResult.run_id) : undefined}
        onReset={lastResult ? () => resetMutation.mutate(lastResult.run_id) : undefined}
        replayPending={replayMutation.isPending}
        resetPending={resetMutation.isPending}
      />

      <SimulationFeed running={running} />

      {hostId && (
        <RawLogTail hostId={hostId} hostName={activeHostName} running={running} />
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
