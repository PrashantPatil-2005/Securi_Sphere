"use client";

import { AppProviders } from "@/lib/providers";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { AssistantProvider } from "@/lib/assistant/AssistantProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { AppShell } from "@/components/layout/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { RouteGuard } from "@/components/RouteGuard";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { TimeRangeProvider } from "@/lib/timeRange";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AppProviders>
        <ToastProvider>
          <TimeRangeProvider>
            <AssistantProvider>
              <AppShell>
                <AuthGuard>
                  <RouteGuard>
                    <ErrorBoundary>{children}</ErrorBoundary>
                  </RouteGuard>
                </AuthGuard>
              </AppShell>
            </AssistantProvider>
          </TimeRangeProvider>
        </ToastProvider>
      </AppProviders>
    </ThemeProvider>
  );
}
