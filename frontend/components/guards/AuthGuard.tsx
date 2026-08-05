"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/api";
import { useUser } from "@/lib/hooks/useUser";
import { PageSkeleton } from "@/components/ui/PageSkeleton";

/** Blocks dashboard content until GET /auth/me succeeds; redirects to login on failure. */
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

  if (isLoading && !data) {
    return <PageSkeleton />;
  }

  if ((isError || !data) && isFetched) {
    return (
      <div className="py-16 text-center text-muted text-sm">
        Redirecting to sign in…
      </div>
    );
  }

  return <>{children}</>;
}
