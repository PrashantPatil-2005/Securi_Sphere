"use client";

import { DashboardProviders } from "@/components/layout/DashboardProviders";
import { AppShell } from "@/components/layout/AppShell";
import { AuthGuard } from "@/components/guards/AuthGuard";
import { RouteGuard } from "@/components/guards/RouteGuard";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <DashboardProviders>
      <AppShell>
        <AuthGuard>
          <RouteGuard>
            <ErrorBoundary>{children}</ErrorBoundary>
          </RouteGuard>
        </AuthGuard>
      </AppShell>
    </DashboardProviders>
  );
}
