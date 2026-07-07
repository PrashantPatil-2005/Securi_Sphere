"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface UserMe {
  id: string;
  email: string;
  full_name: string | null;
  role: { id: string; name: string; description: string | null; permissions: Record<string, string> };
}

export function useUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api<UserMe>("/api/v1/auth/me"),
    staleTime: 300_000,
    retry: false,
    refetchOnWindowFocus: false,
  });
}

export function canAccessRoute(role: string | undefined, href: string): boolean {
  if (!role) return true;
  if (role === "admin") return true;

  const adminOnly = ["/audit", "/rules", "/system"];
  if (adminOnly.some((p) => href === p || href.startsWith(`${p}/`))) {
    return false;
  }

  if (role === "viewer") {
    const viewerBlocked = ["/reports", "/simulation"];
    if (viewerBlocked.some((p) => href === p || href.startsWith(`${p}/`))) {
      return false;
    }
  }

  return true;
}

export function canPurgeSimulation(role: string | undefined): boolean {
  return role === "admin";
}
