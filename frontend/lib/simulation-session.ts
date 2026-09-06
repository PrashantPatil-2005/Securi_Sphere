"use client";

import { useEffect, useState } from "react";

const SESSION_KEY = "securi_simulation_dashboard_session";
const SESSION_EVENT = "securi-simulation-session";

export function enableSimulationDashboardSession(): void {
  localStorage.setItem(SESSION_KEY, "1");
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function disableSimulationDashboardSession(): void {
  localStorage.removeItem(SESSION_KEY);
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export function isSimulationDashboardSessionActive(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(SESSION_KEY) === "1";
}

export function simulationQueryParams(): Record<string, string> {
  return isSimulationDashboardSessionActive() ? { include_simulated: "true" } : {};
}

export function useSimulationQueryParams(): Record<string, string> {
  const [active, setActive] = useState(false);

  useEffect(() => {
    const sync = () => setActive(isSimulationDashboardSessionActive());
    sync();
    window.addEventListener(SESSION_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(SESSION_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return active ? { include_simulated: "true" } : {};
}
