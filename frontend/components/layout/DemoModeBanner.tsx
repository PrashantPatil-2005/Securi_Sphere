"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FlaskConical, X } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  disableSimulationDashboardSession,
  isSimulationDashboardSessionActive,
} from "@/lib/simulation-session";

const DISMISS_KEY = "securi_demo_banner_dismissed";
const SESSION_EVENT = "securi-simulation-session";

interface PublicSettings {
  demo_mode?: boolean;
}

export function DemoModeBanner() {
  const queryClient = useQueryClient();
  const [dismissed, setDismissed] = useState(true);
  const [sessionActive, setSessionActive] = useState(false);

  useEffect(() => {
    setDismissed(localStorage.getItem(DISMISS_KEY) === "1");
    const sync = () => setSessionActive(isSimulationDashboardSessionActive());
    sync();
    window.addEventListener(SESSION_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(SESSION_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const { data } = useQuery({
    queryKey: ["settings", "public"],
    queryFn: () => api<PublicSettings>("/api/v1/settings/public"),
    staleTime: 120_000,
  });

  if (!data || dismissed) return null;

  const showPilot = !!data.demo_mode;
  const showSimCharts = !showPilot && sessionActive;

  if (!showPilot && !showSimCharts) return null;

  const message = showPilot
    ? "Pilot demo mode is on. Charts may include Attack Lab simulation unless exclusion is enabled."
    : "Dashboard charts include simulated Attack Lab data for this session.";

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 px-4 lg:px-6 py-2 text-sm border-b border-accent/25 bg-accent/10 text-foreground"
    >
      <div className="flex items-center gap-2 min-w-0">
        <FlaskConical className="w-4 h-4 shrink-0 text-accent" aria-hidden />
        <span className="truncate sm:whitespace-normal">{message}</span>
        {showPilot && (
          <Link href="/simulation" className="shrink-0 text-accent hover:underline text-xs font-medium hidden sm:inline">
            Open Attack Lab
          </Link>
        )}
      </div>
      <button
        type="button"
        onClick={() => {
          if (showSimCharts) {
            disableSimulationDashboardSession();
            setSessionActive(false);
            queryClient.invalidateQueries({ queryKey: ["siem"] });
            queryClient.invalidateQueries({ queryKey: ["alerts"] });
            queryClient.invalidateQueries({ queryKey: ["offenses"] });
            queryClient.invalidateQueries({ queryKey: ["overview"] });
          }
          localStorage.setItem(DISMISS_KEY, "1");
          setDismissed(true);
        }}
        className="shrink-0 p-1 rounded hover:bg-accent/15 transition-colors"
        aria-label="Dismiss demo notice"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
