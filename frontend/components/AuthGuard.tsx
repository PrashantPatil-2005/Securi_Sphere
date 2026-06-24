"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/api";
import { useUser } from "@/lib/hooks/useUser";
import { PageSkeleton } from "@/components/ui/PageSkeleton";

/** Blocks dashboard until GET /auth/me succeeds; redirects to login on failure. */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data, isLoading, isError, isFetched } = useUser();

  useEffect(() => {
    if (isError) {
      clearTokens();
      const next = pathname && pathname !== "/" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${next}`);
    }
  }, [isError, router, pathname]);

  if (isLoading || !isFetched) {
    return (
      <div className="p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 text-center text-muted text-sm">
        Redirecting to sign in…
      </div>
    );
  }

  return <>{children}</>;
}
