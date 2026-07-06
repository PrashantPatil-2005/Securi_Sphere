"use client";

import Link from "next/link";
import { ChevronRight, Search, Server } from "lucide-react";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { cn } from "@/lib/utils/cn";

interface AlertHit {
  id: string;
  title: string;
  severity: string;
  status: string;
}

interface EventHit {
  id: string;
  event_type: string;
  severity: string;
  description: string | null;
  timestamp?: string;
}

interface HostHit {
  id: string;
  name: string;
  hostname?: string | null;
  status: string;
  ip?: string | null;
}

export function AlertResultRow({ alert, className }: { alert: AlertHit; className?: string }) {
  return (
    <Link
      href={`/alerts?selected=${alert.id}`}
      className={cn(
        "block panel p-3 hover:border-border hover:bg-[var(--sidebar-hover)] transition-colors group",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <SeverityBadge severity={alert.severity} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{alert.title}</p>
          <p className="text-xs text-muted capitalize mt-0.5">{alert.status}</p>
        </div>
        <ChevronRight className="w-4 h-4 text-muted shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden />
      </div>
    </Link>
  );
}

export function EventResultRow({ event, className }: { event: EventHit; className?: string }) {
  return (
    <Link
      href={`/events?q=${encodeURIComponent(event.event_type)}`}
      className={cn(
        "block panel p-3 hover:border-border hover:bg-[var(--sidebar-hover)] transition-colors group",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <SeverityBadge severity={event.severity} />
        <div className="flex-1 min-w-0">
          <p className="font-mono text-xs text-accent">{event.event_type}</p>
          {event.description && <p className="text-sm text-muted mt-1 line-clamp-2">{event.description}</p>}
          {event.timestamp && (
            <p className="text-[11px] text-muted mt-1 tabular-nums">{new Date(event.timestamp).toLocaleString()}</p>
          )}
        </div>
        <ChevronRight className="w-4 h-4 text-muted shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden />
      </div>
    </Link>
  );
}

export function HostResultRow({ host, className }: { host: HostHit; className?: string }) {
  return (
    <Link
      href="/hosts"
      className={cn(
        "block panel p-3 hover:border-border hover:bg-[var(--sidebar-hover)] transition-colors group",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
          <Server className="w-4 h-4 text-accent" aria-hidden />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">{host.name}</p>
          <p className="text-xs text-muted mt-0.5 capitalize">
            {host.status}
            {host.ip ? ` · ${host.ip}` : ""}
            {host.hostname ? ` · ${host.hostname}` : ""}
          </p>
        </div>
        <ChevronRight className="w-4 h-4 text-muted shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden />
      </div>
    </Link>
  );
}

export function SearchResultsSummary({
  events,
  alerts,
  hosts,
  backend,
}: {
  events: number;
  alerts: number;
  hosts?: number;
  backend?: string;
}) {
  return (
    <p className="text-sm text-muted mb-4">
      {events} event{events !== 1 ? "s" : ""} · {alerts} alert{alerts !== 1 ? "s" : ""}
      {hosts != null && <> · {hosts} host{hosts !== 1 ? "s" : ""}</>}
      {backend && (
        <>
          {" "}· backend <span className="font-mono text-xs">{backend}</span>
        </>
      )}
    </p>
  );
}

export function SearchResultsEmpty({
  description,
  onTryNl,
}: {
  description: string;
  onTryNl?: () => void;
}) {
  return (
    <EmptyState
      title="No results"
      description={description}
      icon={<Search />}
      actionLabel={onTryNl ? "Try natural language" : undefined}
      onAction={onTryNl}
    />
  );
}

export function SearchResultSection({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  if (count === 0) return null;
  return (
    <Panel title={`${title} (${count})`}>
      <div className="space-y-2">{children}</div>
    </Panel>
  );
}
