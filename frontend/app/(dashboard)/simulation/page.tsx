"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";

export default function SimulationPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: hosts = [], isLoading: hostsLoading } = useHostsList();
  const [hostId, setHostId] = useState("");
  const [scenario, setScenario] = useState("");

  const { data: scenariosData, isLoading: scenariosLoading } = useQuery({
    queryKey: ["simulation", "scenarios"],
    queryFn: () => api<{ scenarios: string[] }>("/api/v1/simulation/scenarios"),
    retry: false,
  });

  const scenarios = scenariosData?.scenarios ?? [];

  useEffect(() => {
    if (!hostId && hosts[0]) setHostId(hosts[0].id);
  }, [hosts, hostId]);

  useEffect(() => {
    if (!scenario && scenarios[0]) setScenario(scenarios[0]);
  }, [scenarios, scenario]);

  const runMutation = useMutation({
    mutationFn: () =>
      api<{ message: string; events: number }>(
        `/api/v1/simulation/run/${scenario}?host_id=${hostId}`,
        { method: "POST" },
      ),
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
      toast("success", `${r.message} (${r.events} events)`);
    },
    onError: (e: Error) => toast("error", "Simulation failed", e.message),
  });

  const loading = hostsLoading || scenariosLoading;

  return (
    <div className="space-y-6">
      <PageHeader title="Attack Simulation" subtitle="Inject synthetic events to test detection and correlation (admin only)" />
      {loading ? (
        <TableSkeleton rows={4} />
      ) : scenarios.length === 0 ? (
        <EmptyState title="Simulation unavailable" description="Admin access required or simulation disabled in this environment." />
      ) : (
        <Panel title="Run scenario">
          <div className="max-w-lg space-y-4">
            <div>
              <label className="text-sm text-muted block mb-1">Target host</label>
              <select value={hostId} onChange={(e) => setHostId(e.target.value)} className="input-siem w-full">
                {hosts.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm text-muted block mb-1">Scenario</label>
              <select value={scenario} onChange={(e) => setScenario(e.target.value)} className="input-siem w-full">
                {scenarios.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => runMutation.mutate()}
              disabled={!hostId || !scenario || runMutation.isPending}
              className="px-4 py-2 bg-red-700 hover:bg-red-600 rounded text-sm disabled:opacity-50"
            >
              Run simulation
            </button>
          </div>
        </Panel>
      )}
    </div>
  );
}
