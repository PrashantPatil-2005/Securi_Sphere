import { memo, type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface CardProps {
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
  hoverable?: boolean;
}

export const Card = memo(function Card({
  children,
  className,
  noPadding,
  hoverable,
}: CardProps) {
  return (
    <div
      className={cn(
        "panel",
        !noPadding && "panel-body",
        hoverable && "hover:border-border transition-all duration-150 hover:shadow-md",
        className,
      )}
    >
      {children}
    </div>
  );
});

export const CardHeader = memo(function CardHeader({
  title,
  subtitle,
  action,
  className,
}: {
  title: ReactNode;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("panel-header", className)}>
      <div>
        <h3 className="panel-title">{title}</h3>
        {subtitle && <p className="panel-subtitle">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
});
