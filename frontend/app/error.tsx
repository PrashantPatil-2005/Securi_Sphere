"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="ambient-bg min-h-screen flex items-center justify-center p-6">
      <div className="max-w-md w-full glass-panel p-8 text-center space-y-4">
        <div className="flex justify-center">
          <AlertTriangle className="w-12 h-12 text-danger" aria-hidden />
        </div>
        <h1 className="text-display text-foreground">Something went wrong</h1>
        <p className="text-body text-muted">
          An unexpected error occurred. You can retry or return to the dashboard.
        </p>
        <div className="flex flex-wrap gap-3 justify-center pt-2">
          <Button onClick={() => reset()}>Try again</Button>
          <Link href="/" className="btn-ghost inline-flex items-center px-4 py-2">
            Go to dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
