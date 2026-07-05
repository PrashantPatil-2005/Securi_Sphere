"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface AssistantContextPayload {
  alertId?: string;
  offenseId?: string;
  siemQuery?: string;
  prefill?: string;
}

interface AssistantContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
  context: AssistantContextPayload;
  openWithContext: (ctx: AssistantContextPayload) => void;
  clearContext: () => void;
}

const AssistantContext = createContext<AssistantContextValue | null>(null);

export function AssistantProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState<AssistantContextPayload>({});

  const toggle = useCallback(() => setOpen((v) => !v), []);

  const openWithContext = useCallback((ctx: AssistantContextPayload) => {
    setContext(ctx);
    setOpen(true);
  }, []);

  const clearContext = useCallback(() => setContext({}), []);

  const value = useMemo(
    () => ({
      open,
      setOpen,
      toggle,
      context,
      openWithContext,
      clearContext,
    }),
    [open, context, toggle, openWithContext, clearContext],
  );

  return <AssistantContext.Provider value={value}>{children}</AssistantContext.Provider>;
}

export function useAssistant() {
  const ctx = useContext(AssistantContext);
  if (!ctx) throw new Error("useAssistant must be used within AssistantProvider");
  return ctx;
}
