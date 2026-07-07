"use client";

import Link from "next/link";
import { ArrowRight, Clock, Server, ShieldAlert, LayoutDashboard } from "lucide-react";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";

interface Props {
  offenseId?: string;
  hostId?: string;
  hostName?: string;
  incidentId?: string;
  alertId?: string;
}

export function InvestigationTrail({ offenseId, hostId, hostName, incidentId, alertId }: Props) {
  const workspaceLink = alertId
    ? workspaceHref({ alertId })
    : offenseId
      ? workspaceHref({ offenseId })
      : incidentId
        ? workspaceHref({ incidentId })
        : "/investigation";

  const steps = [
    { label: "Alerts", href: "/alerts", icon: ShieldAlert },
    ...(offenseId ? [{ label: "Offense", href: workspaceHref({ offenseId }), icon: ShieldAlert }] : []),
    ...(hostId ? [{ label: hostName || "Host", href: `/hosts`, icon: Server }] : []),
    { label: "Timeline", href: hostId ? `/timeline?host=${hostId}` : "/timeline", icon: Clock },
    ...(incidentId ? [{ label: "Incidents", href: "/incidents", icon: LayoutDashboard }] : []),
    {
      label: "Case Workspace",
      href: workspaceLink,
      icon: incidentId || alertId || offenseId ? LayoutDashboard : ArrowRight,
    },
  ];

  return (
    <nav className="flex flex-wrap items-center gap-2 text-caption normal-case text-muted py-2 border-b border-border-subtle mb-4" aria-label="Investigation workflow">
      {steps.map((step, i) => (
        <span key={step.label} className="flex items-center gap-2">
          {i > 0 && <span className="text-muted/50">→</span>}
          <Link href={step.href} className="inline-flex items-center gap-1 hover:text-accent transition-colors">
            <step.icon className="w-3.5 h-3.5" />
            {step.label}
          </Link>
        </span>
      ))}
    </nav>
  );
}
