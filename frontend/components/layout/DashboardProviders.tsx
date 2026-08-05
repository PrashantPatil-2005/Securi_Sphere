"use client";

import { type ReactNode } from "react";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { AppProviders } from "@/lib/providers";
import { ToastProvider } from "@/components/ui/Toast";
import { TimeRangeProvider } from "@/lib/timeRange";
import { AssistantProvider } from "@/lib/assistant/AssistantProvider";

/**
 * Composes all context providers needed by dashboard pages.
 * Reduces nesting from 5 separate wrapper components to 1.
 */
export function DashboardProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <AppProviders>
        <ToastProvider>
          <TimeRangeProvider>
            <AssistantProvider>{children}</AssistantProvider>
          </TimeRangeProvider>
        </ToastProvider>
      </AppProviders>
    </ThemeProvider>
  );
}
