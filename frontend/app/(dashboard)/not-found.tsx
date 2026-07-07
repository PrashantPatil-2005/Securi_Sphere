import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { PageHeader, EmptyState } from "@/components/ui/Panel";

export default function DashboardNotFound() {
  return (
    <div className="space-y-6">
      <PageHeader title="Page not found" subtitle="The requested page does not exist in this workspace" />
      <EmptyState
        title="Not found"
        description="Check the URL or press Ctrl+K to jump to another page."
        icon={<FileQuestion className="w-10 h-10 opacity-40" />}
        action="/"
        actionLabel="Go to Dashboard"
      />
      <Link href="/search" className="btn-ghost text-sm inline-flex">
        Open SIEM Search
      </Link>
    </div>
  );
}
