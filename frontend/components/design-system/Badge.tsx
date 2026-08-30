import { memo } from "react";
import { cn } from "@/lib/utils/cn";
import { SEVERITY_META, type Severity } from "@/lib/design/tokens";

type BadgeVariant = "severity" | "status" | "default";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  severity?: Severity;
  status?: string;
  className?: string;
  dot?: boolean;
}

const severityTone: Record<Severity, string> = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
  info: "badge-info",
};

const severityDotColor: Record<Severity, string> = {
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
  info: "bg-severity-info",
};

const statusTone: Record<string, string> = {
  new: "status-new",
  open: "status-new",
  investigating: "status-investigating",
  in_progress: "status-investigating",
  resolved: "status-resolved",
  closed: "status-closed",
  false_positive: "status-closed",
  online: "status-resolved",
  offline: "status-closed",
  degraded: "status-investigating",
  healthy: "status-resolved",
  active: "status-new",
};

function BadgeInner({
  children,
  variant = "default",
  severity,
  status,
  className,
  dot = false,
}: BadgeProps) {
  let toneClass = "";
  let dotColor = "";

  if (variant === "severity" && severity) {
    toneClass = severityTone[severity] || "badge-info";
    dotColor = severityDotColor[severity] || "bg-severity-info";
  } else if (variant === "status" && status) {
    const key = status.toLowerCase().replace(/\s+/g, "_");
    toneClass = statusTone[key] || "badge-info";
    const meta = STATUS_DOT_COLORS[key];
    dotColor = meta || "bg-muted";
  }

  return (
    <span className={cn("badge", toneClass, className)}>
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full", dotColor)} />}
      {children}
    </span>
  );
}

const STATUS_DOT_COLORS: Record<string, string> = {
  new: "bg-accent",
  open: "bg-accent",
  investigating: "bg-warning",
  in_progress: "bg-warning",
  resolved: "bg-success",
  closed: "bg-muted",
  false_positive: "bg-muted",
  online: "bg-success",
  offline: "bg-danger",
  degraded: "bg-warning",
  healthy: "bg-success",
  active: "bg-success",
};

export const Badge = memo(BadgeInner);

export const SeverityBadge = memo(function SeverityBadge({
  severity,
  className,
}: {
  severity: string;
  className?: string;
}) {
  const key = (severity?.toLowerCase() || "info") as Severity;
  const meta = SEVERITY_META[key] || SEVERITY_META.info;
  return (
    <Badge variant="severity" severity={key} className={className}>
      {meta.label}
    </Badge>
  );
});

export const StatusBadge = memo(function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  return (
    <Badge variant="status" status={status} dot className={className}>
      {STATUS_META_LABELS[status?.toLowerCase()] || status}
    </Badge>
  );
});

const STATUS_META_LABELS: Record<string, string> = {
  new: "New",
  open: "Open",
  investigating: "Investigating",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
  false_positive: "False Positive",
  online: "Online",
  offline: "Offline",
  degraded: "Degraded",
  healthy: "Healthy",
  active: "Active",
};
