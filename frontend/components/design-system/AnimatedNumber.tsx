"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";

interface AnimatedNumberProps {
  /** The number the counter should settle on. */
  value: number;
  /** Formats each intermediate value. Defaults to an en-US string rounded to the target's precision. */
  format?: (value: number) => string;
  /** How long the transition takes, in milliseconds. */
  duration?: number;
  className?: string;
}

const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);

function decimalsOf(value: number): number {
  const text = String(value);
  const dot = text.indexOf(".");
  return dot === -1 ? 0 : text.length - dot - 1;
}

/**
 * Counts from the previously shown number (or 0 on first mount) up or down to
 * `value`, easing out over `duration` ms. Falls back to showing the final
 * value instantly when the user prefers reduced motion or the value is not a
 * finite number.
 */
export function AnimatedNumber({
  value,
  format,
  duration = 600,
  className,
}: AnimatedNumberProps) {
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(() => (reduceMotion ? value : 0));
  const displayRef = useRef(reduceMotion ? value : 0);

  useEffect(() => {
    if (!Number.isFinite(value) || reduceMotion) {
      displayRef.current = value;
      setDisplay(value);
      return;
    }
    const from = displayRef.current;
    if (from === value) return;
    const startedAt = performance.now();
    let rafId = 0;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / duration);
      const current = from + (value - from) * easeOutCubic(progress);
      displayRef.current = current;
      setDisplay(current);
      if (progress < 1) rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, [value, duration, reduceMotion]);

  const decimals = decimalsOf(value);
  const text =
    typeof format === "function"
      ? format(display)
      : Number.isFinite(display)
        ? display.toLocaleString("en-US", {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
          })
        : String(display);

  return <span className={className}>{text}</span>;
}
