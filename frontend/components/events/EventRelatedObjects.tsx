"use client";

import { memo } from "react";
import Link from "next/link";
import { AlertTriangle, Shield, FileText } from "lucide-react";
import { SeverityBadge } from "@/components/design-system/Badge";


interface RelatedAlert {
  id: string;
  title: string;
  severity: string;
  status: string;
}

interface RelatedOffense {
  id: string;
  offense_number: number;
  title: string;
  risk_level: string;
  status: string;
}

interface RelatedIncident {
  id: string;
  title: string;
  severity: string;
  status: string;
}

interface EventRelatedObjectsProps {
  alerts?: RelatedAlert[];
  offenses?: RelatedOffense[];
  incidents?: RelatedIncident[];
}

function RelatedSection({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {icon}
        <h4 className="text-xs font-medium text-muted uppercase tracking-wide">{title}</h4>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function EventRelatedObjectsInner({ alerts, offenses, incidents }: EventRelatedObjectsProps) {
  const hasAny = (alerts && alerts.length > 0) || (offenses && offenses.length > 0) || (incidents && incidents.length > 0);

  if (!hasAny) {
    return (
      <div className="text-xs text-muted italic py-2">
        No related security objects found for this event.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {alerts && alerts.length > 0 && (
        <RelatedSection
          icon={<AlertTriangle className="w-3.5 h-3.5 text-severity-high" />}
          title={`Related Alerts (${alerts.length})`}
        >
          {alerts.map((a) => (
            <Link
              key={a.id}
              href={`/alerts/${a.id}`}
              className="flex items-center gap-2 p-2 rounded-lg border border-border-subtle hover:border-border hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <SeverityBadge severity={a.severity} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">{a.title}</p>
                <p className="text-[10px] text-muted capitalize">{a.status}</p>
              </div>
            </Link>
          ))}
        </RelatedSection>
      )}

      {offenses && offenses.length > 0 && (
        <RelatedSection
          icon={<Shield className="w-3.5 h-3.5 text-severity-critical" />}
          title={`Related Offenses (${offenses.length})`}
        >
          {offenses.map((o) => (
            <Link
              key={o.id}
              href={`/offenses/${o.id}`}
              className="flex items-center gap-2 p-2 rounded-lg border border-border-subtle hover:border-border hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <SeverityBadge severity={o.risk_level} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">
                  #{o.offense_number} — {o.title}
                </p>
                <p className="text-[10px] text-muted capitalize">{o.status}</p>
              </div>
            </Link>
          ))}
        </RelatedSection>
      )}

      {incidents && incidents.length > 0 && (
        <RelatedSection
          icon={<FileText className="w-3.5 h-3.5 text-severity-medium" />}
          title={`Related Incidents (${incidents.length})`}
        >
          {incidents.map((inc) => (
            <Link
              key={inc.id}
              href={`/incidents/${inc.id}`}
              className="flex items-center gap-2 p-2 rounded-lg border border-border-subtle hover:border-border hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <SeverityBadge severity={inc.severity} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">{inc.title}</p>
                <p className="text-[10px] text-muted capitalize">{inc.status}</p>
              </div>
            </Link>
          ))}
        </RelatedSection>
      )}
    </div>
  );
}

export const EventRelatedObjects = memo(EventRelatedObjectsInner);
