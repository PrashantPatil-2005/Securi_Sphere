"use client";

import { useCallback, useEffect } from "react";

type KeyboardListNavOptions = {
  enabled?: boolean;
  itemCount: number;
  activeIndex: number;
  setActiveIndex: (index: number | ((prev: number) => number)) => void;
  onActivate?: (index: number) => void;
  onToggle?: (index: number) => void;
  onBulkResolve?: () => void;
  onBulkInvestigate?: () => void;
};

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

/** j/k and arrow keys for list focus; Space toggles; Enter opens; r/i bulk shortcuts. */
export function useKeyboardListNav({
  enabled = true,
  itemCount,
  activeIndex,
  setActiveIndex,
  onActivate,
  onToggle,
  onBulkResolve,
  onBulkInvestigate,
}: KeyboardListNavOptions) {
  const clamp = useCallback((idx: number) => Math.max(0, Math.min(itemCount - 1, idx)), [itemCount]);

  useEffect(() => {
    if (!enabled || itemCount === 0) return;

    const onKeyDown = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;

      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) => clamp(typeof prev === "number" ? prev + 1 : 0));
        return;
      }
      if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((prev) => clamp(typeof prev === "number" ? prev - 1 : 0));
        return;
      }
      if (e.key === "Enter" && onActivate) {
        e.preventDefault();
        onActivate(activeIndex);
        return;
      }
      if (e.key === " " && onToggle) {
        e.preventDefault();
        onToggle(activeIndex);
        return;
      }
      if (e.key === "r" && onBulkResolve) {
        e.preventDefault();
        onBulkResolve();
        return;
      }
      if (e.key === "i" && onBulkInvestigate) {
        e.preventDefault();
        onBulkInvestigate();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    enabled,
    itemCount,
    activeIndex,
    clamp,
    setActiveIndex,
    onActivate,
    onToggle,
    onBulkResolve,
    onBulkInvestigate,
  ]);
}
