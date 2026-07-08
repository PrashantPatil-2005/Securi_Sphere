"use client";

import { createContext, useContext, useEffect, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { setTelemetryEnabled } from "./telemetry";

export interface UxFeatureFlags {
  dynamic_ux_enabled: boolean;
  ux_activation_coach_enabled: boolean;
  ux_live_simulation_enabled: boolean;
  ux_enrollment_handshake_enabled: boolean;
  ux_guided_triage_enabled: boolean;
  ux_dashboard_vitality_enabled: boolean;
  ux_admin_ops_console_enabled: boolean;
}

export interface PublicSettingsWithUx {
  telemetry_enabled?: boolean;
  ux_flags?: UxFeatureFlags;
}

const DEFAULT_UX_FLAGS: UxFeatureFlags = {
  dynamic_ux_enabled: true,
  ux_activation_coach_enabled: true,
  ux_live_simulation_enabled: true,
  ux_enrollment_handshake_enabled: true,
  ux_guided_triage_enabled: true,
  ux_dashboard_vitality_enabled: true,
  ux_admin_ops_console_enabled: true,
};

const FeatureFlagsContext = createContext<UxFeatureFlags>(DEFAULT_UX_FLAGS);

export function FeatureFlagsProvider({ children }: { children: ReactNode }) {
  const { data } = useQuery({
    queryKey: ["settings", "public"],
    queryFn: () => api<PublicSettingsWithUx>("/api/v1/settings/public"),
    staleTime: 60_000,
  });

  useEffect(() => {
    setTelemetryEnabled(data?.telemetry_enabled !== false);
  }, [data?.telemetry_enabled]);

  const flags = { ...DEFAULT_UX_FLAGS, ...data?.ux_flags };

  return (
    <FeatureFlagsContext.Provider value={flags}>
      {children}
    </FeatureFlagsContext.Provider>
  );
}

export function useFeatureFlags(): UxFeatureFlags {
  return useContext(FeatureFlagsContext);
}

export function useUxEnabled(flag: keyof UxFeatureFlags): boolean {
  const flags = useFeatureFlags();
  return flags.dynamic_ux_enabled && flags[flag];
}
