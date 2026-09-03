"use client";

import { useEffect, useState } from "react";
import { WifiOff, X } from "lucide-react";
import { useWsConnected } from "@/lib/websocket";
import { useOnline } from "@/lib/hooks/useOnline";

export function ConnectionBanner() {
  const online = useOnline();
  const wsConnected = useWsConnected();
  const [dismissed, setDismissed] = useState(false);

  const hasIssue = !online || !wsConnected;

  useEffect(() => {
    if (online && wsConnected) setDismissed(false);
  }, [online, wsConnected]);

  if (!hasIssue || dismissed) return null;

  const message = !online
    ? "You're offline"
    : "Live feed disconnected";

  return (
    <div className="flex items-center justify-center gap-2 px-4 py-1 text-[11px] text-muted bg-warning/5 border-b border-warning/20">
      <WifiOff className="w-3 h-3 shrink-0 text-warning/70" aria-hidden />
      <span>{message}</span>
      <span className="text-muted/50">·</span>
      <span className="text-muted/60">Reconnecting…</span>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="shrink-0 p-0.5 rounded hover:bg-warning/10 transition-colors ml-1"
        aria-label="Dismiss connection notice"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}
