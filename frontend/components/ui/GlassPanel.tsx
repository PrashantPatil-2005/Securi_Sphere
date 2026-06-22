import { memo, type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface GlassPanelProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  padding?: boolean;
}

export const GlassPanel = memo(function GlassPanel({
  children,
  className,
  hover = false,
  padding = true,
}: GlassPanelProps) {
  return (
    <div
      className={cn(
        "glass-panel",
        hover && "transition-colors duration-150 hover:border-border",
        padding && "p-4",
        className,
      )}
    >
      {children}
    </div>
  );
});
