"use client";

import { useEffect, useId, useRef, useState } from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";

export function HelpTooltip({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  const [visible, setVisible] = useState(false);
  const id = useId();
  const rootRef = useRef<HTMLSpanElement>(null);
  const isTouch = useMediaQuery("(pointer: coarse)");

  useEffect(() => {
    if (!visible || !isTouch) return;
    const onOutside = (e: MouseEvent | TouchEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setVisible(false);
      }
    };
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("touchstart", onOutside);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("touchstart", onOutside);
    };
  }, [visible, isTouch]);

  return (
    <span ref={rootRef} className={cn("relative inline-flex items-center", className)}>
      <button
        type="button"
        className="text-muted hover:text-foreground transition-colors p-0.5"
        aria-describedby={visible ? id : undefined}
        aria-expanded={isTouch ? visible : undefined}
        onMouseEnter={isTouch ? undefined : () => setVisible(true)}
        onMouseLeave={isTouch ? undefined : () => setVisible(false)}
        onFocus={isTouch ? undefined : () => setVisible(true)}
        onBlur={isTouch ? undefined : () => setVisible(false)}
        onClick={isTouch ? () => setVisible((v) => !v) : undefined}
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
