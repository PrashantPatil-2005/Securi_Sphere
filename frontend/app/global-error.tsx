"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";

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
    <html lang="en">
      <body className="antialiased min-h-screen bg-background text-foreground font-sans">
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
              <button
                type="button"
                onClick={() => reset()}
                className="btn-primary inline-flex items-center px-4 py-2"
              >
                Try again
              </button>
              <a href="/" className="btn-ghost inline-flex items-center px-4 py-2">
                Go to dashboard
              </a>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
