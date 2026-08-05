"use client";

import { usePathname } from "next/navigation";
import { ShieldOff } from "lucide-react";
import { useUser, canAccessRoute } from "@/lib/hooks/useUser";
import { EmptyState, PageHeader } from "@/components/ui/Panel";

/** Blocks page content when the signed-in role cannot access the current route. */
export function RouteGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: user } = useUser();
  const role = user?.role?.name;

  if (!role || !pathname) {
    return <>{children}</>;
  }

  if (!canAccessRoute(role, pathname)) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Access denied"
          subtitle="Your account does not have permission to view this page"
        />
        <EmptyState
          title="Insufficient permissions"
          description={`The ${role} role cannot access this section. Ask an administrator if you need elevated access.`}
          icon={<ShieldOff className="w-10 h-10 opacity-40" />}
          action="/"
          actionLabel="Go to Dashboard"
        />
      </div>
    );
  }

  return <>{children}</>;
}
