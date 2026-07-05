"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Circle, ListChecks } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Panel } from "@/components/ui/Panel";

const STORAGE_KEY = "securi_onboarding_done";

interface Step {
  id: string;
  label: string;
  href: string;
  check: (data: { hosts: number; alerts: number }) => boolean;
}

const STEPS: Step[] = [
  {
    id: "host",
    label: "Add and enroll a host",
    href: "/hosts",
    check: (d) => d.hosts >= 1,
  },
  {
    id: "simulation",
    label: "Run an attack simulation",
    href: "/simulation",
    check: () => false,
  },
  {
    id: "triage",
    label: "Triage an open alert",
    href: "/alerts",
    check: (d) => d.alerts >= 1,
  },
];

export function OnboardingChecklist() {
  const [dismissed, setDismissed] = useState(true);
  const [simDone, setSimDone] = useState(false);

  useEffect(() => {
    setDismissed(localStorage.getItem(STORAGE_KEY) === "1");
    setSimDone(localStorage.getItem("securi_onboarding_sim") === "1");
  }, []);

  const { data: overview } = useQuery({
    queryKey: ["overview"],
    queryFn: () =>
      api<{ total_hosts: number; active_alerts: number }>("/api/v1/overview"),
    staleTime: 30_000,
  });

  const progress = {
    hosts: overview?.total_hosts ?? 0,
    alerts: overview?.active_alerts ?? 0,
  };

  const completed = STEPS.filter((s) => {
    if (s.id === "simulation") return simDone;
    return s.check(progress);
  }).length;

  if (dismissed || completed >= STEPS.length) return null;

  return (
    <Panel
      title="Getting started"
      subtitle={`${completed}/${STEPS.length} complete — finish the SOC lab walkthrough`}
      action={
        <button
          type="button"
          className="btn-ghost text-xs"
          onClick={() => {
            localStorage.setItem(STORAGE_KEY, "1");
            setDismissed(true);
          }}
        >
          Dismiss
        </button>
      }
    >
      <ul className="space-y-2">
        {STEPS.map((step) => {
          const done =
            step.id === "simulation" ? simDone : step.check(progress);
          return (
            <li key={step.id}>
              <Link
                href={step.href}
                onClick={() => {
                  if (step.id === "simulation") {
                    localStorage.setItem("securi_onboarding_sim", "1");
                    setSimDone(true);
                  }
                }}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--sidebar-hover)] transition-colors"
              >
                {done ? (
                  <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-muted shrink-0" />
                )}
                <span className={done ? "text-muted line-through text-sm" : "text-sm"}>
                  {step.label}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
      <p className="text-caption normal-case text-muted mt-3 flex items-center gap-1.5">
        <ListChecks className="w-3.5 h-3.5" />
        Tip: press Ctrl+K for quick navigation
      </p>
    </Panel>
  );
}
