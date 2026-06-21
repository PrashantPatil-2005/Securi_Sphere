"use client";

import { AppProviders } from "@/lib/providers";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { AppShell } from "@/components/layout/AppShell";
import { AuthSync } from "@/components/AuthSync";
import { TimeRangeProvider } from "@/lib/timeRange";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AppProviders>
        <ToastProvider>
          <TimeRangeProvider>
            <AuthSync />
            <AppShell>{children}</AppShell>
          </TimeRangeProvider>
        </ToastProvider>
      </AppProviders>
    </ThemeProvider>
  );
}
