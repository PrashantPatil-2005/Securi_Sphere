"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "bottom" | "left" | "right";
  className?: string;
}

const sideClasses = {
  top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
  bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
  left: "right-full top-1/2 -translate-y-1/2 mr-2",
  right: "left-full top-1/2 -translate-y-1/2 ml-2",
};

export function Tooltip({
  content,
  children,
  side = "top",
  className,
}: TooltipProps) {
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
    <span ref={rootRef} className={cn("relative inline-flex", className)}>
      <span
        onMouseEnter={isTouch ? undefined : () => setVisible(true)}
        onMouseLeave={isTouch ? undefined : () => setVisible(false)}
        onFocus={isTouch ? undefined : () => setVisible(true)}
        onBlur={isTouch ? undefined : () => setVisible(false)}
        onClick={isTouch ? () => setVisible((v) => !v) : undefined}
        aria-describedby={visible ? id : undefined}
      >
        {children}
      </span>
      {visible && (
        <span
          id={id}
          role="tooltip"
          className={cn(
            "tooltip pointer-events-none animate-fade-in",
            sideClasses[side],
          )}
        >
          {content}
        </span>
      )}
    </span>
  );
}
