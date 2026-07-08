"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { isOnboardingSearchCompleted } from "@/lib/onboarding";

export interface OnboardingProgress {
  hosts: number;
  simulationRuns: number;
  triagedAlerts: number;
  offenses: number;
  incidents: number;
  notificationsConfigured: boolean;
  searchCompleted: boolean;
}

export interface OnboardingStepDef {
  id: string;
  label: string;
  href: string;
  isComplete: (p: OnboardingProgress) => boolean;
}

export const ONBOARDING_STEPS: OnboardingStepDef[] = [
  {
    id: "host",
    label: "Add a host (or skip with Attack Lab only)",
    href: "/hosts",
    isComplete: (p) => p.hosts >= 1,
  },
  {
    id: "simulation",
    label: "Run an attack in the Attack Lab",
    href: "/simulation",
    isComplete: (p) => p.simulationRuns >= 1,
  },
  {
    id: "triage",
    label: "Triage an open alert",
    href: "/alerts",
    isComplete: (p) => p.triagedAlerts >= 1,
  },
  {
    id: "offense",
    label: "Review an offense and promote to incident",
    href: "/offenses",
    isComplete: (p) => p.incidents >= 1,
  },
  {
    id: "search",
    label: "Run a saved search or SIEM query",
    href: "/search",
    isComplete: (p) => p.searchCompleted,
  },
  {
    id: "notifications",
    label: "Configure notification channels",
    href: "/settings",
    isComplete: (p) => p.notificationsConfigured,
  },
];

async function fetchAlertTotal(status: string): Promise<number> {
  const res = await api<{ total?: number }>(`/api/v1/alerts?status=${status}&page_size=1`);
  return res.total ?? 0;
}

export function useOnboardingProgress() {
  const [searchCompleted, setSearchCompleted] = useState(false);

  useEffect(() => {
    const refresh = () => setSearchCompleted(isOnboardingSearchCompleted());
    refresh();
    window.addEventListener("storage", refresh);
    window.addEventListener("securi-onboarding-update", refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("securi-onboarding-update", refresh);
    };
  }, []);

  const { data: overview } = useQuery({
    queryKey: ["overview"],
    queryFn: () =>
      api<{ total_hosts: number }>("/api/v1/overview"),
    staleTime: 30_000,
  });

  const { data: simulationRuns = 0 } = useQuery({
    queryKey: ["simulation", "runs", "count"],
    queryFn: async () => {
      const res = await api<{ total: number }>("/api/v1/simulation/runs?page_size=1");
      return res.total ?? 0;
    },
    staleTime: 30_000,
    retry: false,
  });

  const { data: investigatingAlerts = 0 } = useQuery({
    queryKey: ["alerts", "count", "investigating"],
    queryFn: () => fetchAlertTotal("investigating"),
    staleTime: 30_000,
  });

  const { data: resolvedAlerts = 0 } = useQuery({
    queryKey: ["alerts", "count", "resolved"],
    queryFn: () => fetchAlertTotal("resolved"),
    staleTime: 30_000,
  });

  const { data: offenseCount = 0 } = useQuery({
    queryKey: ["offenses", "count"],
    queryFn: async () => {
      const res = await api<{ total?: number }>("/api/v1/offenses?page_size=1");
      return res.total ?? 0;
    },
    staleTime: 30_000,
  });

  const { data: incidentCount = 0 } = useQuery({
    queryKey: ["incidents", "count"],
    queryFn: async () => {
      const items = await api<unknown[]>("/api/v1/incidents");
      return items.length;
    },
    staleTime: 30_000,
  });

  const { data: notifSettings } = useQuery({
    queryKey: ["notification-settings"],
    queryFn: () =>
      api<{
        email_enabled: boolean;
        telegram_enabled: boolean;
        slack_enabled: boolean;
      }>("/api/v1/notifications/settings"),
    staleTime: 60_000,
  });

  const progress: OnboardingProgress = {
    hosts: overview?.total_hosts ?? 0,
    simulationRuns,
    triagedAlerts: investigatingAlerts + resolvedAlerts,
    offenses: offenseCount,
    incidents: incidentCount,
    notificationsConfigured: !!(
      notifSettings?.email_enabled ||
      notifSettings?.telegram_enabled ||
      notifSettings?.slack_enabled
    ),
    searchCompleted,
  };

  const completedCount = ONBOARDING_STEPS.filter((s) => s.isComplete(progress)).length;

  useEffect(() => {
    const key = "securi_onboarding_completed_steps";
    const prev = JSON.parse(sessionStorage.getItem(key) ?? "[]") as string[];
    const now = ONBOARDING_STEPS.filter((s) => s.isComplete(progress)).map((s) => s.id);
    for (const id of now) {
      if (!prev.includes(id)) {
        import("@/lib/telemetry").then(({ track }) => track("onboarding_step_completed", { step_id: id }));
      }
    }
    sessionStorage.setItem(key, JSON.stringify(now));
  }, [progress]);

  return {
    progress,
    steps: ONBOARDING_STEPS,
    completedCount,
    totalSteps: ONBOARDING_STEPS.length,
    refreshSearchCompleted: () => setSearchCompleted(isOnboardingSearchCompleted()),
  };
}
