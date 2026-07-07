"use client";

import Link from "next/link";
import { CheckCircle2, ExternalLink } from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { GuidedInvestigationBar } from "@/components/attack-lab/GuidedInvestigationBar";
import type { SimulationRunResult } from "@/lib/types/simulation";

interface Props {
  result: SimulationRunResult | null;
  onRunAgain: () => void;
}

function buildEventsLink(hostId: string): string {
  const params = new URLSearchParams({ host_id: hostId, include_simulated: "true" });
  return `/events?${params.toString()}`;
}

export function SimulationResults({ result, onRunAgain }: Props) {
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

  return (
    <GlassPanel className="space-y-4">
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
            <p className="text-2xl font-semibold tabular-nums text-accent">{stat.value}</p>
            <p className="text-xs text-muted mt-0.5">{stat.label}</p>
          </div>
        ))}
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
        <button type="button" className="btn-primary text-sm" onClick={onRunAgain}>
          Run again
        </button>
      </div>
    </GlassPanel>
  );
}
