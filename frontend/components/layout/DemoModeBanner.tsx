"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FlaskConical, X } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const DISMISS_KEY = "securi_demo_banner_dismissed";

interface PublicSettings {
  demo_mode?: boolean;
  simulation_enabled?: boolean;
  exclude_simulated_from_dashboard?: boolean;
}

export function DemoModeBanner() {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(localStorage.getItem(DISMISS_KEY) === "1");
  }, []);

  const { data } = useQuery({
    queryKey: ["settings", "public"],
    queryFn: () => api<PublicSettings>("/api/v1/settings/public"),
    staleTime: 120_000,
  });

  if (!data || dismissed) return null;

  const showPilot = !!data.demo_mode;
  const showSimCharts =
    !showPilot &&
    data.simulation_enabled &&
    data.exclude_simulated_from_dashboard === false;

  if (!showPilot && !showSimCharts) return null;

  const message = showPilot
    ? "Pilot demo mode — run Multi-Stage Attack in Attack Lab, then follow the guided investigation bar. Demo login: demo@securi.local / Demo1234!"
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
