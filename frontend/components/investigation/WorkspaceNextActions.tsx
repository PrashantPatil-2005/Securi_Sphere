"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import type { InvestigationWorkspace } from "@/lib/types/investigation";
import { Panel } from "@/components/ui/Panel";

interface Props {
  data: InvestigationWorkspace;
  onPromote?: (offenseId: string) => void;
  promotePending?: boolean;
  onAskAi?: () => void;
}

export function WorkspaceNextActions({ data, onPromote, promotePending, onAskAi }: Props) {
  const { alert, offense, incident, host, timelines } = data;

  const actions: Array<
    | { type: "link"; label: string; href: string; primary?: boolean }
    | { type: "button"; label: string; onClick: () => void; primary?: boolean; disabled?: boolean }
  > = [];

  if (offense && !offense.incident_id && onPromote) {
    actions.push({
      type: "button",
      label: "Promote to incident",
      onClick: () => onPromote(offense.id),
      primary: true,
      disabled: promotePending,
    });
  }

  if (alert?.status === "open") {
    actions.push({
      type: "link",
      label: "Triage in alerts",
      href: `/alerts?selected=${alert.id}`,
    });
  }

  if (host && timelines.length > 0) {
    actions.push({
      type: "link",
      label: "View attack timeline",
      href: `/timeline?host=${host.id}`,
      primary: !offense?.incident_id,
    });
  } else if (host) {
    actions.push({
      type: "link",
      label: "View timelines",
      href: `/timeline?host=${host.id}`,
    });
  }

  if (alert?.mitre_technique_id) {
    actions.push({
      type: "link",
      label: `MITRE ${alert.mitre_technique_id}`,
      href: `/mitre?technique=${alert.mitre_technique_id}`,
    });
  }

  if (offense) {
    actions.push({
      type: "link",
      label: "Offense detail",
      href: `/offenses?selected=${offense.id}`,
    });
  }

  if (incident) {
    actions.push({
      type: "link",
      label: "Incident record",
      href: `/incidents?selected=${incident.id}`,
    });
  }

  if (onAskAi) {
    actions.push({
      type: "button",
      label: "Ask AI",
      onClick: onAskAi,
    });
  }

  if (actions.length === 0) return null;

  return (
    <Panel title="Next actions" subtitle="Recommended steps for this case">
      <div className="flex flex-wrap gap-2">
        {actions.map((action) =>
          action.type === "link" ? (
            <Link
              key={action.label}
              href={action.href}
              className={action.primary ? "btn-primary text-xs inline-flex items-center gap-1" : "btn-ghost text-xs inline-flex items-center gap-1"}
            >
              {action.label}
              {action.primary && <ArrowRight className="w-3 h-3" />}
            </Link>
          ) : (
            <button
              key={action.label}
              type="button"
              className={action.primary ? "btn-primary text-xs inline-flex items-center gap-1" : "btn-ghost text-xs inline-flex items-center gap-1"}
              onClick={action.onClick}
              disabled={action.disabled}
            >
              {action.label === "Ask AI" && <Sparkles className="w-3 h-3" />}
              {action.label}
            </button>
          ),
        )}
      </div>
    </Panel>
  );
}
