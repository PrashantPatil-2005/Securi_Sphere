import { memo, type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";
import type { Severity } from "@/lib/design/tokens";

interface TimelineItemProps {
  severity?: Severity;
  title: string;
  description?: string;
  timestamp?: string;
  children?: ReactNode;
  className?: string;
}

export const TimelineItem = memo(function TimelineItem({
  severity = "info",
  title,
  description,
  timestamp,
  children,
  className,
}: TimelineItemProps) {
  return (
    <div className={cn("timeline-item", className)}>
      <div className={cn("timeline-dot", `timeline-dot-${severity}`)} />
      <div>
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium text-foreground">{title}</span>
          {timestamp && (
            <time className="text-[10px] font-medium text-muted tabular-nums">
              {timestamp}
            </time>
          )}
        </div>
        {description && (
          <p className="text-xs text-muted mt-0.5 leading-relaxed">{description}</p>
        )}
        {children}
      </div>
    </div>
  );
});
