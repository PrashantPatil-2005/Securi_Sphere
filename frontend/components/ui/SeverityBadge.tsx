import { memo } from "react";

const TONE: Record<string, string> = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
  info: "badge-info",
};

function SeverityBadgeInner({ severity, className = "" }: { severity: string; className?: string }) {
  const key = severity?.toLowerCase() || "info";
  return <span className={`badge ${TONE[key] || TONE.info} ${className}`}>{severity}</span>;
}

export const SeverityBadge = memo(SeverityBadgeInner);
