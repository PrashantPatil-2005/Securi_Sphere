"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  variant?: "page" | "inline" | "card";
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description,
  onRetry,
  variant = "card",
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 text-center",
        variant === "page" && "py-20 px-6",
        variant === "card" && "py-10 px-4",
        variant === "inline" && "py-4 px-2",
        className,
      )}
      role="alert"
    >
      <div
        className={cn(
          "flex items-center justify-center rounded-xl bg-danger/10 text-danger",
          variant === "page" ? "w-16 h-16" : "w-10 h-10",
        )}
      >
        <AlertTriangle className={cn(variant === "page" ? "w-8 h-8" : "w-5 h-5")} />
      </div>
      <div>
        <p
          className={cn(
            "font-medium text-foreground",
            variant === "page" ? "text-base" : "text-sm",
          )}
        >
          {title}
        </p>
        {description && (
          <p className="text-sm text-muted mt-1 max-w-sm">{description}</p>
        )}
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="btn-ghost inline-flex items-center gap-2 mt-1"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </button>
      )}
    </div>
  );
}
