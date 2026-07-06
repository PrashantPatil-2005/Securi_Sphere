"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { useBodyScrollLock } from "@/lib/hooks/useBodyScrollLock";
import { useFocusTrap } from "@/lib/hooks/useFocusTrap";
import { cn } from "@/lib/utils/cn";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  side?: "right" | "bottom";
  className?: string;
}

export function Drawer({
  open,
  onClose,
  title,
  description,
  children,
  side = "right",
  className,
}: DrawerProps) {
  const panelRef = useRef<HTMLElement>(null);
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

  const isBottom = side === "bottom";

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex",
        isBottom ? "flex-col justify-end" : "justify-end",
      )}
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-label="Close drawer"
        onClick={onClose}
      />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        className={cn(
          "relative glass-nav shadow-2xl overflow-y-auto",
          isBottom
            ? "w-full max-h-[85vh] rounded-t-xl border-t animate-slide-up p-5"
            : "w-full max-w-md h-full border-l animate-slide-in-right p-6",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-3 mb-6">
          <div>
            <h2 id={titleId} className="page-title">
              {title}
            </h2>
            {description && (
              <p id={descId} className="text-caption normal-case text-muted mt-1">
                {description}
              </p>
            )}
          </div>
          <button type="button" onClick={onClose} className="btn-ghost p-2 shrink-0" aria-label="Close drawer">
            <X className="w-4 h-4" />
          </button>
        </div>
        {children}
      </aside>
    </div>
  );
}
