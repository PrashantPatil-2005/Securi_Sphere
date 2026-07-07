import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import type { SimulationRunResult } from "@/lib/types/simulation";

export interface GuidedInvestigationStep {
  id: string;
  label: string;
  href: string;
  hint: string;
  available: boolean;
}

export function buildGuidedInvestigationSteps(result: SimulationRunResult): GuidedInvestigationStep[] {
  const firstAlert = result.alert_ids[0];
  const firstOffense = result.offense_ids[0];
  const firstTimeline = result.timeline_ids[0];

  const workspaceHrefValue = firstOffense
    ? workspaceHref({ offenseId: firstOffense })
    : firstAlert
      ? workspaceHref({ alertId: firstAlert })
      : "/investigation";

  return [
    {
      id: "alerts",
      label: "Triage alerts",
      href: firstAlert ? `/alerts?selected=${firstAlert}` : "/alerts",
      hint: "Open the investigation pane and start triage",
      available: result.alert_ids.length > 0,
    },
    {
      id: "offenses",
      label: "Review offense",
      href: firstOffense ? `/offenses?selected=${firstOffense}` : "/offenses",
      hint: "Correlated activity grouped from simulation",
      available: result.offense_ids.length > 0,
    },
    {
      id: "workspace",
      label: "Open Case Workspace",
      href: workspaceHrefValue,
      hint: "Unified alert, offense, host, and event view",
      available: result.alert_ids.length > 0 || result.offense_ids.length > 0,
    },
    {
      id: "timeline",
      label: "Attack timeline",
      href: firstTimeline
        ? `/timeline?timeline=${firstTimeline}`
        : `/timeline?host=${result.host_id}`,
      hint: "Reconstructed kill chain with MITRE chips",
      available: result.timeline_ids.length > 0 || result.events > 0,
    },
    {
      id: "mitre",
      label: "MITRE coverage",
      href: "/mitre",
      hint: "Heatmap and technique drilldown",
      available: true,
    },
    {
      id: "incidents",
      label: "Incidents",
      href: "/incidents",
      hint: "Formal record after promoting an offense",
      available: result.offense_ids.length > 0,
    },
  ];
}
