import type { ReactNode } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils/cn";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("empty-state", className)} role="status">
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
