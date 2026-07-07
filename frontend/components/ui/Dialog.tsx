"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { useBodyScrollLock } from "@/lib/hooks/useBodyScrollLock";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { cn } from "@/lib/utils/cn";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  className?: string;
  size?: "md" | "lg" | "xl";
  showHeader?: boolean;
  align?: "center" | "top";
  zIndex?: number;
}

const sizes = {
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-2xl",
};

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  className,
  size = "lg",
  showHeader = true,
  align = "center",
  zIndex = 50,
}: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();

  useBodyScrollLock(open);
  useFocusTrap(panelRef, open);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className={cn(
        "fixed inset-0 flex justify-center p-4",
        align === "top" ? "items-start pt-[15vh]" : "items-center",
      )}
      style={{ zIndex }}
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        className={cn(
          "relative w-full panel shadow-2xl animate-scale-in max-h-[min(90vh,720px)] overflow-y-auto",
          showHeader ? "p-5" : "overflow-hidden",
          sizes[size],
          className,
        )}
      >
        {!showHeader && (
          <p id={titleId} className="sr-only">
            {title}
          </p>
        )}
        {showHeader && (
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <h2 id={titleId} className="text-subheading text-foreground">
                {title}
              </h2>
              {description && (
                <p id={descId} className="text-caption normal-case text-muted mt-1">
                  {description}
                </p>
              )}
            </div>
            <button type="button" onClick={onClose} className="btn-ghost p-2 shrink-0" aria-label="Close">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
