"use client";

import Link from "next/link";
import { CheckCircle2, ExternalLink, FolderSearch, RotateCcw, ShieldAlert, Trash2 } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { Button } from "@/components/ui/Button";
import { GuidedInvestigationBar } from "@/components/attack-lab/GuidedInvestigationBar";
import { AnimatedNumber } from "@/components/design-system/AnimatedNumber";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { groupByStage, stageForRule } from "@/lib/attackChain";
import type { SimulationAlert, SimulationRunResult } from "@/lib/types/simulation";

interface Props {
  result: SimulationRunResult | null;
  onRunAgain: () => void;
  onReplay?: () => void;
  onReset?: () => void;
  replayPending?: boolean;
  resetPending?: boolean;
}

function buildEventsLink(hostId: string): string {
  const params = new URLSearchParams({ host_id: hostId, include_simulated: "true" });
  return `/events?${params.toString()}`;
}

/** Alerts grouped into kill-chain stages, most severe first inside each stage. */
function FiredAlertChain({ alerts }: { alerts: SimulationAlert[] }) {
  const groups = groupByStage(
    alerts,
    (alert) => stageForRule(alert.rule_type),
    (alert) => alert.severity,
  );

  return (
    <ol className="space-y-3">
      {groups.map((group) => (
        <li key={group.stage.label} className="flex gap-3">
          <div className="flex flex-col items-center shrink-0">
            <span className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-semibold border border-accent bg-accent/10 text-accent">
              {group.stage.rank}
            </span>
            <span className="w-px flex-1 min-h-[1rem] bg-border-subtle mt-1" />
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <p className="text-sm font-medium">{group.stage.label}</p>
            <ul className="mt-1 space-y-1">
              {group.items.map((alert) => (
                <li
                  key={alert.id}
                  className="flex flex-wrap items-center gap-2 rounded-md border border-border-subtle px-2.5 py-1.5"
                >
                  <SeverityBadge severity={alert.severity} />
                  <span className="text-sm min-w-0 truncate">{alert.title}</span>
                  {alert.rule_type && (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                      {alert.rule_type}
                    </span>
                  )}
                  {alert.mitre_technique_id && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/40 text-muted border border-border-subtle">
                      {alert.mitre_technique_id}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function SimulationResults({
  result,
  onRunAgain,
  onReplay,
  onReset,
  replayPending,
  resetPending,
}: Props) {
  if (!result) {
    return (
      <GlassPanel>
        <h2 className="text-subheading mb-2">Results</h2>
        <p className="text-sm text-muted">
          Run a simulation to see injected events, alerts, offenses, and timeline links here.
        </p>
      </GlassPanel>
    );
  }

  const timelineHref =
    result.timeline_ids.length > 0
      ? `/timeline?timeline=${result.timeline_ids[0]}`
      : "/timeline";

  const links = [
    { href: buildEventsLink(result.host_id), label: "View events", count: result.event_ids.length },
    { href: "/alerts", label: "View alerts", count: result.alert_ids.length },
    { href: "/offenses", label: "View offenses", count: result.offense_ids.length },
    { href: timelineHref, label: "Attack timeline", count: result.timeline_ids.length },
  ];

  // Deep link into Case Workspace: prefer a promoted incident, then an offense,
  // then the first alert — so analysts always land on the richest case view.
  const incidentIds = result.incident_ids ?? [];
  const caseWorkspaceHref =
    incidentIds.length > 0
      ? workspaceHref({ incidentId: incidentIds[0] })
      : result.offense_ids.length > 0
        ? workspaceHref({ offenseId: result.offense_ids[0] })
        : result.alert_ids.length > 0
          ? workspaceHref({ alertId: result.alert_ids[0] })
          : null;

  const expected = result.expected_alerts ?? [];
  const firedCount = result.alerts?.length ?? 0;

  return (
    <GlassPanel className="space-y-4">
      <EmotionBanner
        tone="success"
        title="Simulation complete — your SOC is alive"
        message={`${result.events} events generated across detection, correlation, and timelines.`}
      />
      <div className="flex items-start gap-3">
        <CheckCircle2 className="w-5 h-5 text-success shrink-0 mt-0.5" />
        <div>
          <h2 className="text-subheading">Simulation complete</h2>
          <p className="text-sm font-medium">{result.name}</p>
          <p className="text-sm text-muted mt-1">{result.message}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Events", value: result.events },
          { label: "Alerts", value: result.alert_ids.length },
          { label: "Offenses", value: result.offense_ids.length },
          { label: "Timelines", value: result.timeline_ids.length },
        ].map((stat) => (
          <div key={stat.label} className="rounded-lg border border-border-subtle p-3 text-center">
            <p className="text-2xl font-semibold tabular-nums text-accent">
              <AnimatedNumber value={stat.value} />
            </p>
            <p className="text-xs text-muted mt-0.5">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-border-subtle p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
          <h3 className="text-subheading flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-accent" />
            What actually fired
          </h3>
          {expected.length > 0 && (
            <p className="text-xs text-muted">
              <span className="font-semibold tabular-nums text-foreground">
                <AnimatedNumber value={firedCount} />
              </span>{" "}
              of{" "}
              <span className="font-semibold tabular-nums text-foreground">
                {expected.length}
              </span>{" "}
              expected detections raised
            </p>
          )}
        </div>

        {firedCount > 0 ? (
          <FiredAlertChain alerts={result.alerts} />
        ) : (
          <p className="text-sm text-muted">
            No detections were raised for this run — the events landed, but no rule threshold was
            crossed on this host.
          </p>
        )}
      </div>

      <GuidedInvestigationBar result={result} />

      <div className="flex flex-wrap gap-2">
        {links.map((link) => (
          <Link key={link.href} href={link.href} className="btn-ghost text-sm inline-flex items-center gap-1.5">
            {link.label}
            {link.count > 0 && <span className="text-muted">({link.count})</span>}
            <ExternalLink className="w-3 h-3 opacity-60" />
          </Link>
        ))}
        {caseWorkspaceHref && (
          <Link
            href={caseWorkspaceHref}
            className="btn-primary text-sm inline-flex items-center gap-1.5"
            title="Synthetic demo data — this case was generated by the Demo Center"
          >
            <FolderSearch className="w-3.5 h-3.5" />
            Open Case Workspace
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-200 border border-amber-500/40">
              SYNTHETIC
            </span>
          </Link>
        )}
        {onReplay && result.scenario !== "custom" && (
          <Button type="button" variant="ghost" size="sm" disabled={replayPending} loading={replayPending} onClick={onReplay}>
            <RotateCcw className="w-3.5 h-3.5" />
            Replay this run
          </Button>
        )}
        {onReset && (
          <Button type="button" variant="ghost" size="sm" disabled={resetPending} loading={resetPending} onClick={onReset}>
            <Trash2 className="w-3.5 h-3.5" />
            Reset this run
          </Button>
        )}
        <button type="button" className="btn-primary text-sm" onClick={onRunAgain}>
          Run again
        </button>
      </div>
    </GlassPanel>
  );
}
