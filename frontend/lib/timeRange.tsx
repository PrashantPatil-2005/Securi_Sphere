"use client";

import { createContext, useContext, useMemo, useState, ReactNode } from "react";

export const TIME_PRESETS = [
  { value: "15m", label: "Last 15 Minutes" },
  { value: "30m", label: "Last 30 Minutes" },
  { value: "1h", label: "Last 1 Hour" },
  { value: "6h", label: "Last 6 Hours" },
  { value: "12h", label: "Last 12 Hours" },
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

  const queryParams = useMemo(() => {
    const p: Record<string, string> = {};
    if (range.preset === "custom") {
      if (range.from) p.from = new Date(range.from).toISOString();
      if (range.to) p.to = new Date(range.to).toISOString();
    } else if (range.preset) {
      p.preset = range.preset;
    }
    return p;
  }, [range]);

  const value: TimeRangeContextValue = {
    range,
    setPreset: (preset) => setRange((r) => ({ ...r, preset })),
    setFrom: (from) => setRange((r) => ({ ...r, from })),
    setTo: (to) => setRange((r) => ({ ...r, to })),
    queryParams,
  };

  return <TimeRangeContext.Provider value={value}>{children}</TimeRangeContext.Provider>;
}

export function useTimeRange() {
  const ctx = useContext(TimeRangeContext);
  if (!ctx) throw new Error("useTimeRange must be used within TimeRangeProvider");
  return ctx;
}
