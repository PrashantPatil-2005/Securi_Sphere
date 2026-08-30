"use client";

import { memo } from "react";
import Link from "next/link";
import { Target, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { Card, CardHeader, EmptyState } from "@/components/design-system";
import type { Alert } from "@/lib/types/alert";

interface AlertMitreProps {
  alert: Alert;
}

const TACTIC_LABELS: Record<string, string> = {
  initial_access: "Initial Access",
  execution: "Execution",
  persistence: "Persistence",
  privilege_escalation: "Privilege Escalation",
  defense_evasion: "Defense Evasion",
  credential_access: "Credential Access",
  discovery: "Discovery",
  lateral_movement: "Lateral Movement",
  collection: "Collection",
  exfiltration: "Exfiltration",
  command_and_control: "Command and Control",
  impact: "Impact",
  resource_development: "Resource Development",
  reconnaissance: "Reconnaissance",
};

function formatTacticName(tactic: string): string {
  return TACTIC_LABELS[tactic] || tactic.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function AlertMitreInner({ alert }: AlertMitreProps) {
  return (
    <Card>
      <CardHeader title="MITRE ATT&CK" />
      <div className="p-4">
        {alert.mitre_technique_id || alert.mitre_tactic ? (
          <div className="space-y-3">
            {alert.mitre_tactic && (
              <div className="space-y-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                  Tactic
                </span>
                <p className="text-sm text-foreground font-medium">
                  {formatTacticName(alert.mitre_tactic)}
                </p>
              </div>
            )}

            {alert.mitre_technique_id && (
              <div className="space-y-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-muted">
                  Technique
                </span>
                <p className="text-sm text-foreground font-medium">
                  {alert.mitre_technique_id}
                </p>
              </div>
            )}

            <Link
              href={`/mitre?technique=${encodeURIComponent(alert.mitre_technique_id || "")}`}
              className={cn(
                "inline-flex items-center gap-1.5 text-xs font-medium",
                "text-accent hover:underline",
              )}
            >
              View in MITRE Navigator
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        ) : (
          <EmptyState
            title="No MITRE ATT&CK mapping available."
            icon={<Target className="w-5 h-5" />}
          />
        )}
      </div>
    </Card>
  );
}

export const AlertMitre = memo(AlertMitreInner);
