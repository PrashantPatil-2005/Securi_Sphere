"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/ui/Panel";

export default function DashboardError({
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
    <div className="space-y-6">
      <PageHeader title="Something went wrong" subtitle="This page failed to load" />
      <EmptyState
        title="Unexpected error"
        description="An error occurred while loading this page. You can retry or return to the dashboard."
        icon={<AlertTriangle className="w-10 h-10 text-danger" />}
        onAction={reset}
        actionLabel="Try again"
      />
      <Link href="/" className="btn-ghost text-sm inline-flex">
        Go to Dashboard
      </Link>
    </div>
  );
}
