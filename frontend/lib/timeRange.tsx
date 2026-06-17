"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export const TIME_PRESETS = [
  { value: "today", label: "Today" },
  { value: "24h", label: "Last 24 Hours" },
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
  { value: "90d", label: "Last 90 Days" },
  { value: "custom", label: "Custom Range" },
] as const;

export type TimePreset = (typeof TIME_PRESETS)[number]["value"];

export interface TimeRangeState {
  preset: TimePreset;
  from: string;
  to: string;
}

interface TimeRangeContextValue {
  range: TimeRangeState;
  setPreset: (preset: TimePreset) => void;
  setFrom: (from: string) => void;
  setTo: (to: string) => void;
  queryParams: Record<string, string>;
}

const TimeRangeContext = createContext<TimeRangeContextValue | null>(null);

export function TimeRangeProvider({ children }: { children: ReactNode }) {
  const [range, setRange] = useState<TimeRangeState>({ preset: "24h", from: "", to: "" });

  const setPreset = useCallback((preset: TimePreset) => setRange((r) => ({ ...r, preset })), []);
  const setFrom = useCallback((from: string) => setRange((r) => ({ ...r, from })), []);
  const setTo = useCallback((to: string) => setRange((r) => ({ ...r, to })), []);

  const queryParams = useMemo(() => {
    const p: Record<string, string> = {};
    if (range.preset === "custom") {
      if (range.from) p.from = new Date(range.from).toISOString();
      if (range.to) p.to = new Date(range.to).toISOString();
    } else if (range.preset) {
      p.preset = range.preset;
    }
    return p;
  }, [range.preset, range.from, range.to]);

  const value = useMemo(
    () => ({ range, setPreset, setFrom, setTo, queryParams }),
    [range, setPreset, setFrom, setTo, queryParams],
  );

  return <TimeRangeContext.Provider value={value}>{children}</TimeRangeContext.Provider>;
}

export function useTimeRange() {
  const ctx = useContext(TimeRangeContext);
  if (!ctx) throw new Error("useTimeRange must be used within TimeRangeProvider");
  return ctx;
}
