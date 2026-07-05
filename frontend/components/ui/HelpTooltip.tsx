"use client";

import { useId, useState } from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export function HelpTooltip({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  const [visible, setVisible] = useState(false);
  const id = useId();

  return (
    <span className={cn("relative inline-flex items-center", className)}>
      <button
        type="button"
        className="text-muted hover:text-foreground transition-colors p-0.5"
        aria-describedby={visible ? id : undefined}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        aria-label="Help"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>
      {visible && (
        <span
          id={id}
          role="tooltip"
          className="absolute left-1/2 -translate-x-1/2 top-full mt-1.5 z-50 w-56 px-2.5 py-2 text-[11px] normal-case text-left rounded-md border border-border bg-card shadow-lg text-muted"
        >
          {content}
        </span>
      )}
    </span>
  );
}
