"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { workspaceHref } from "@/lib/hooks/useDeepLinkedSelection";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { InvestigationWorkspacePane } from "@/components/investigation/InvestigationWorkspacePane";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { Drawer } from "@/components/ui/Drawer";
import { TableSkeleton } from "@/components/ui/Skeleton";

function CaseNavigatorContent({
  alertId,
  offenseId,
  incidentId,
  onClear,
}: {
  alertId: string | null;
  offenseId: string | null;
  incidentId: string | null;
  onClear: () => void;
}) {
  return (
    <div className="text-sm space-y-2">
      {alertId && (
        <p>
          <span className="text-muted">Alert</span>
          <br />
          <span className="font-mono text-xs break-all">{alertId}</span>
        </p>
      )}
      {offenseId && (
        <p>
          <span className="text-muted">Offense</span>
          <br />
          <span className="font-mono text-xs break-all">{offenseId}</span>
        </p>
      )}
      {incidentId && (
        <p>
          <span className="text-muted">Incident</span>
          <br />
          <span className="font-mono text-xs break-all">{incidentId}</span>
        </p>
      )}
      <button type="button" className="btn-ghost text-xs mt-2" onClick={onClear}>
        Clear case
      </button>
    </div>
  );
}

export default function InvestigationPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={8} />}>
      <InvestigationPageContent />
    </Suspense>
  );
}

function InvestigationPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const alertId = searchParams.get("alert");
  const offenseId = searchParams.get("offense");
  const incidentId = searchParams.get("incident");
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [navOpen, setNavOpen] = useState(false);

  const hasAnchor = !!(alertId || offenseId || incidentId);

  const { data: recentAlerts } = useQuery({
    queryKey: ["alerts", "workspace-picker"],
    queryFn: () => api<{ items: { id: string; title: string; severity: string; status: string }[] }>(
      "/api/v1/alerts?page_size=10&status=open",
    ),
    enabled: !hasAnchor,
  });

  const clearCase = () => {
    setNavOpen(false);
    router.push("/investigation");
  };

  const caseLabel = alertId
    ? "Alert case"
    : offenseId
      ? "Offense case"
      : incidentId
        ? "Incident case"
        : "Active case";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Case Workspace"
        subtitle="Unified view across alerts, offenses, and incidents — one pane for the full SOC narrative"
      />

      {!hasAnchor ? (
        <div className="grid lg:grid-cols-2 gap-6">
          <Panel title="Start an investigation">
            <EmptyState
              title="No case selected"
              description="Open a case from an alert, offense, or incident — or pick a recent open alert below."
            />
            {recentAlerts?.items && recentAlerts.items.length > 0 && (
              <ul className="mt-4 space-y-2">
                {recentAlerts.items.map((a) => (
                  <li key={a.id}>
                    <Link
                      href={workspaceHref({ alertId: a.id })}
                      className="block p-3 rounded-lg border border-border-subtle hover:bg-[var(--sidebar-hover)] text-sm"
                    >
                      <span className="font-medium">{a.title}</span>
                      <span className="text-muted ml-2 capitalize">{a.severity}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-2 mt-4">
              <Link href="/alerts" className="btn-ghost text-sm">Browse alerts</Link>
              <Link href="/offenses" className="btn-ghost text-sm">Browse offenses</Link>
              <Link href="/incidents" className="btn-ghost text-sm">Browse incidents</Link>
            </div>
          </Panel>
        </div>
      ) : (
        <>
          {!isDesktop && (
            <div className="flex items-center justify-between gap-3 p-3 rounded-lg border border-border-subtle bg-[var(--input-bg)] lg:hidden">
              <span className="text-sm font-medium">{caseLabel}</span>
              <button type="button" className="btn-ghost text-xs shrink-0" onClick={() => setNavOpen(true)}>
                Case info
              </button>
            </div>
          )}

          <div className={isDesktop ? "grid lg:grid-cols-[minmax(280px,1fr)_minmax(0,2fr)] gap-6" : "space-y-4"}>
            {isDesktop && (
              <Panel title="Case navigator">
                <CaseNavigatorContent
                  alertId={alertId}
                  offenseId={offenseId}
                  incidentId={incidentId}
                  onClear={clearCase}
                />
              </Panel>
            )}
            <InvestigationWorkspacePane
              alertId={alertId}
              offenseId={offenseId}
              incidentId={incidentId}
            />
          </div>

          <Drawer
            open={navOpen && !isDesktop}
            onClose={() => setNavOpen(false)}
            title="Case navigator"
            side="bottom"
            className="lg:hidden"
          >
            <CaseNavigatorContent
              alertId={alertId}
              offenseId={offenseId}
              incidentId={incidentId}
              onClear={clearCase}
            />
          </Drawer>
        </>
      )}
    </div>
  );
}
