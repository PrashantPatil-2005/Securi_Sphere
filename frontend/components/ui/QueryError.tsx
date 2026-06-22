"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "./Button";

export function QueryError({
  message = "Failed to load data",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="empty-state">
      <div className="mb-3 flex justify-center text-danger">
        <AlertCircle className="w-8 h-8" />
      </div>
      <p className="empty-title">{message}</p>
      <p className="empty-desc">Check your connection or try again.</p>
      {onRetry && (
        <Button variant="ghost" className="mt-4" onClick={onRetry}>
          <RefreshCw className="w-4 h-4" />
          Retry
        </Button>
      )}
    </div>
  );
}
