"use client";

import { AppProviders } from "@/lib/providers";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { AssistantProvider } from "@/lib/assistant/AssistantProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { AppShell } from "@/components/layout/AppShell";
import { AuthGuard } from "@/components/AuthGuard";
import { TimeRangeProvider } from "@/lib/timeRange";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AppProviders>
        <ToastProvider>
          <TimeRangeProvider>
            <AuthGuard>
              <AssistantProvider>
                <AppShell>{children}</AppShell>
              </AssistantProvider>
            </AuthGuard>
          </TimeRangeProvider>
        </ToastProvider>
      </AppProviders>
    </ThemeProvider>
  );
}
