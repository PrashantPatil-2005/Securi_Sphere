"use client";

import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { Button } from "./Button";

export function QueryError({
  message = "Failed to load data",
  description = "Check your connection or try again.",
  onRetry,
  retrying = false,
}: {
  message?: string;
  description?: string;
  onRetry?: () => void;
  retrying?: boolean;
}) {
  return (
    <div className="empty-state" role="alert">
      <div className="mb-3 flex justify-center text-danger">
        <AlertCircle className="w-8 h-8" />
      </div>
      <p className="empty-title">{message}</p>
      <p className="empty-desc">{description}</p>
      {onRetry && (
        <Button variant="ghost" className="mt-4" onClick={onRetry} disabled={retrying}>
          {retrying ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {retrying ? "Retrying…" : "Retry"}
        </Button>
      )}
    </div>
  );
}
