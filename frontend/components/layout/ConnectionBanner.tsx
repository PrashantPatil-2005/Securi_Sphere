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
    ? "You're offline. Live updates are paused until your connection returns."
    : "Live feed disconnected. Reconnecting…";

  return (
    <div
      role="status"
      className="flex items-center justify-between gap-3 px-4 lg:px-6 py-2 text-sm border-b border-warning/30 bg-warning/10 text-warning"
    >
      <div className="flex items-center gap-2 min-w-0">
        <WifiOff className="w-4 h-4 shrink-0" aria-hidden />
        <span>{message}</span>
      </div>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="shrink-0 p-1 rounded hover:bg-warning/20 transition-colors"
        aria-label="Dismiss connection notice"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
