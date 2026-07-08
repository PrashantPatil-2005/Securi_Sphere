import { memo, type ReactNode } from "react";
import Link from "next/link";

interface PanelProps {
  title?: ReactNode;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
}

export const Panel = memo(function Panel({ title, subtitle, action, children, className = "", noPadding }: PanelProps) {
  return (
    <section className={`panel ${className}`}>
      {(title || action) && (
        <header className="panel-header">
          <div>
            {title && <h2 className="panel-title">{title}</h2>}
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <div className={noPadding ? "" : "panel-body"}>{children}</div>
    </section>
  );
});

export const PageHeader = memo(function PageHeader({ title, subtitle, action }: { title: ReactNode; subtitle?: string; action?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {action}
    </header>
  );
});

export const StatCard = memo(function StatCard({
  label,
  value,
  tone = "default",
  href,
  delta,
  deltaLabel,
  vital,
}: {
  label: string;
  value: ReactNode;
  tone?: "default" | "success" | "warning" | "danger" | "info";
  href?: string;
  delta?: number | null;
  deltaLabel?: string;
  vital?: boolean;
}) {
  const card = (
    <div className={`stat-card stat-${tone} ${vital ? "stat-card-vital" : ""}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value ?? "—"}</span>
      {delta != null && (
        <span className={`stat-delta ${delta > 0 ? "stat-delta-up" : delta < 0 ? "stat-delta-down" : "stat-delta-neutral"}`}>
          {delta > 0 ? "+" : ""}{delta}{deltaLabel ? ` ${deltaLabel}` : ""}
        </span>
      )}
    </div>
  );
  if (href) return <Link href={href} className="block">{card}</Link>;
  return card;
});

export function EmptyState({
  title,
  description,
  action,
  actionLabel,
  onAction,
  icon,
}: {
  title: string;
  description?: string;
  action?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: ReactNode;
}) {
  return (
    <div className="empty-state" role="status">
      {icon && <div className="empty-state-icon" aria-hidden>{icon}</div>}
      <p className="empty-title">{title}</p>
      {description && <p className="empty-desc">{description}</p>}
      {actionLabel && onAction && (
        <button type="button" onClick={onAction} className="btn-primary inline-flex mt-4">
          {actionLabel}
        </button>
      )}
      {action && actionLabel && !onAction && (
        <Link href={action} className="btn-primary inline-flex mt-4">
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
