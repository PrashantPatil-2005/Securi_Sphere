"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useHostsList } from "@/lib/hooks/useApiQuery";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { HelpTooltip } from "@/components/ui/HelpTooltip";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";
import { CheckCircle2, FlaskConical, Radio } from "lucide-react";

const STEPS = ["Select target", "Choose scenario", "Run & observe"];

export default function SimulationPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: hosts = [], isLoading: hostsLoading } = useHostsList();
  const [step, setStep] = useState(0);
  const [hostId, setHostId] = useState("");
  const [scenario, setScenario] = useState("");
  const [lastResult, setLastResult] = useState<{ events: number; message: string } | null>(null);

  const { data: scenariosData, isLoading: scenariosLoading, isError, refetch } = useQuery({
    queryKey: ["simulation", "scenarios"],
    queryFn: () => api<{ scenarios: string[] }>("/api/v1/simulation/scenarios"),
    retry: false,
  });

  const scenarios = scenariosData?.scenarios ?? [];

  useEffect(() => {
    if (!hostId && hosts[0]) setHostId(hosts[0].id);
  }, [hosts, hostId]);

  useEffect(() => {
    const list = scenariosData?.scenarios ?? [];
    if (!scenario && list[0]) setScenario(list[0]);
  }, [scenariosData, scenario]);

  const runMutation = useMutation({
    mutationFn: () =>
      api<{ message: string; events: number }>(
        `/api/v1/simulation/run/${scenario}?host_id=${hostId}`,
        { method: "POST" },
      ),
    onSuccess: (r) => {
      setLastResult({ events: r.events, message: r.message });
      setStep(2);
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["offenses"] });
      queryClient.invalidateQueries({ queryKey: ["siem"] });
      queryClient.invalidateQueries({ queryKey: ["timelines"] });
      toast("success", `${r.message} (${r.events} events)`);
    },
    onError: (e: Error) => toast("error", "Simulation failed", e.message),
  });

  const purgeMutation = useMutation({
    mutationFn: () => api<{ message: string; events_deleted: number }>("/api/v1/simulation/purge", { method: "DELETE" }),
    onSuccess: (r) => {
      queryClient.invalidateQueries();
      toast("success", r.message, `${r.events_deleted} simulated events removed`);
    },
    onError: (e: Error) => toast("error", "Purge failed", e.message),
  });

  const loading = hostsLoading || scenariosLoading;

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2">
            Attack Simulation
            <HelpTooltip content="Generate realistic attack events on an enrolled host. Try brute_force or multi_stage_attack, then triage alerts and offenses." />
          </span>
        }
        subtitle="Inject synthetic events for demos. Dashboard charts hide simulated data by default — use Purge when done."
        action={
          <button
            type="button"
            className="btn-ghost text-sm"
            disabled={purgeMutation.isPending}
            onClick={() => purgeMutation.mutate()}
          >
            Purge simulated data
          </button>
        }
      />
      <div className="flex gap-2">
        {STEPS.map((label, i) => (
          <div key={label} className={cn("flex items-center gap-2 text-sm", i <= step ? "text-accent" : "text-muted")}>
            <span className={cn("w-6 h-6 rounded-full flex items-center justify-center text-xs border", i <= step ? "border-accent bg-accent/10" : "border-border-subtle")}>
              {i < step ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
            </span>
            <span className="hidden sm:inline">{label}</span>
          </div>
        ))}
      </div>
      {loading ? (
        <TableSkeleton rows={4} />
      ) : isError ? (
        <QueryError onRetry={() => refetch()} />
      ) : scenarios.length === 0 ? (
        <EmptyState title="Simulation unavailable" description="Admin access required or simulation disabled in this environment." />
      ) : (
        <div className="grid lg:grid-cols-2 gap-6">
          <GlassPanel className="space-y-4">
            {step === 0 && (
              <>
                <h2 className="text-subheading">Step 1 — Target host</h2>
                <select value={hostId} onChange={(e) => setHostId(e.target.value)} className="input-siem w-full">
                  {hosts.map((h) => (
                    <option key={h.id} value={h.id}>{h.name}</option>
                  ))}
                </select>
                <button type="button" className="btn-primary" disabled={!hostId} onClick={() => setStep(1)}>
                  Continue
                </button>
              </>
            )}
            {step === 1 && (
              <>
                <h2 className="text-subheading">Step 2 — Attack scenario</h2>
                <div className="space-y-2">
                  {scenarios.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setScenario(s)}
                      className={cn(
                        "w-full text-left p-3 rounded-lg border transition-colors",
                        scenario === s ? "border-accent bg-accent/10" : "border-border-subtle hover:bg-[var(--sidebar-hover)]",
                      )}
                    >
                      <span className="font-medium capitalize">{s.replace(/_/g, " ")}</span>
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button type="button" className="btn-ghost" onClick={() => setStep(0)}>Back</button>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={!scenario || runMutation.isPending}
                    onClick={() => runMutation.mutate()}
                  >
                    <FlaskConical className="w-4 h-4" />
                    Run simulation
                  </button>
                </div>
              </>
            )}
            {step === 2 && lastResult && (
              <>
                <h2 className="text-subheading">Step 3 — Observe results</h2>
                <p className="text-sm text-muted">{lastResult.message}</p>
                <p className="text-2xl font-semibold tabular-nums text-accent">{lastResult.events} events injected</p>
                <div className="flex flex-wrap gap-2">
                  <a href="/events" className="btn-ghost text-sm">View events</a>
                  <a href="/alerts" className="btn-ghost text-sm">View alerts</a>
                  <a href="/offenses" className="btn-ghost text-sm">View offenses</a>
                  <a href="/timeline" className="btn-ghost text-sm">Attack timeline</a>
                  <button type="button" className="btn-primary text-sm" onClick={() => { setStep(0); setLastResult(null); }}>
                    Run again
                  </button>
                </div>
              </>
            )}
          </GlassPanel>
          <Panel title="Live preview">
            <div className="flex items-center gap-2 text-sm text-muted mb-4">
              <Radio className={cn("w-4 h-4", runMutation.isPending ? "text-accent animate-pulse" : "")} />
              After running, check Events → Offenses → Timeline for the full investigation narrative.
            </div>
            <ol className="text-sm space-y-2 text-muted list-decimal list-inside">
              <li>Brute force events appear in the live feed</li>
              <li>Detection rules create alerts</li>
              <li>Offense engine groups related activity</li>
              <li>Timeline reconstructs the attack chain</li>
            </ol>
          </Panel>
        </div>
      )}
    </div>
  );
}
