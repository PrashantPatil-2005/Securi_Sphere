"use client";

import { useState, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "./queryClient";
import { WebSocketProvider } from "./websocket";
import { FeatureFlagsProvider } from "./featureFlags";

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(createQueryClient);
  return (
    <QueryClientProvider client={client}>
      <FeatureFlagsProvider>
        <WebSocketProvider>{children}</WebSocketProvider>
      </FeatureFlagsProvider>
    </QueryClientProvider>
  );
}
