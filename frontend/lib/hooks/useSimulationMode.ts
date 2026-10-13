"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { api } from "@/lib/api";
import { useHostsList } from "./useApiQuery";
import type { AttackLabTab } from "@/lib/types/simulation";

export interface HostInfo {
  hostId: string;
  hostName: string;
  agentOnline: boolean;
  lastSeen: string | null;
}

const STORAGE_KEY = "simulationMode";
const HOST_KEY = "simulationLiveHostId";
const VALID_TABS: AttackLabTab[] = ["presets", "custom", "history", "live", "replay"];

interface ModeState {
  mode: AttackLabTab;
  hostInfo: HostInfo | null;
}

let state: ModeState = { mode: "presets", hostInfo: null };
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): ModeState {
  return state;
}

function patch(next: Partial<ModeState>) {
  state = { ...state, ...next };
  emit();
}

export function setSimulationMode(mode: AttackLabTab) {
  if (state.mode === mode) return;
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, mode);
  }
  patch({ mode, hostInfo: mode === "live" ? state.hostInfo : null });
}

function setHostInfo(hostInfo: HostInfo | null) {
  if (
    state.hostInfo?.hostId === hostInfo?.hostId &&
    state.hostInfo?.agentOnline === hostInfo?.agentOnline &&
    state.hostInfo?.lastSeen === hostInfo?.lastSeen &&
    state.hostInfo?.hostName === hostInfo?.hostName
  ) {
    return;
  }
  patch({ hostInfo });
}

/** Shared Attack Lab tab state — one source of truth for the page and header. */
export function useSimulationMode(): {
  mode: AttackLabTab;
  setMode: (mode: AttackLabTab) => void;
  hostInfo: HostInfo | null;
} {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const { data: hosts = [] } = useHostsList();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && VALID_TABS.includes(stored as AttackLabTab)) {
      setSimulationMode(stored as AttackLabTab);
    }
    setHydrated(true);
  }, []);

  // Resolve the live host id when entering the Live Linux Lab tab.
  useEffect(() => {
    if (!hydrated || snapshot.mode !== "live") return;
    const storedHostId = localStorage.getItem(HOST_KEY);
    const host =
      hosts.find((h) => h.id === storedHostId) ?? hosts[0];
    if (!host) return;
    localStorage.setItem(HOST_KEY, host.id);
    setHostInfo({
      hostId: host.id,
      hostName: host.name,
      agentOnline: false,
      lastSeen: null,
    });
  }, [hydrated, snapshot.mode, hosts]);

  const liveHostId =
    snapshot.mode === "live" ? snapshot.hostInfo?.hostId ?? null : null;

  // Poll agent status while the Live Linux Lab tab is open.
  useEffect(() => {
    if (!hydrated || !liveHostId) return;

    const hostId = liveHostId;
    let cancelled = false;

    const refresh = async () => {
      try {
        const r = await api<{ status: string; last_seen: string }>(
          `/api/v1/hosts/${hostId}/status`,
        );
        if (cancelled) return;
        setHostInfo({
          hostId,
          hostName: state.hostInfo?.hostName ?? "",
          agentOnline: r.status === "online",
          lastSeen: r.last_seen ?? null,
        });
      } catch {
        if (cancelled) return;
        setHostInfo({
          hostId,
          hostName: state.hostInfo?.hostName ?? "",
          agentOnline: false,
          lastSeen: null,
        });
      }
    };

    refresh();
    const id = setInterval(refresh, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [hydrated, liveHostId]);

  return {
    mode: snapshot.mode,
    setMode: setSimulationMode,
    hostInfo: snapshot.hostInfo,
  };
}
