"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

/**
 * Syncs a query param with local selection state (read on mount + write on change).
 */
export function useDeepLinkedSelection(param = "selected") {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedId, setSelectedIdState] = useState<string | null>(() => searchParams.get(param));

  useEffect(() => {
    const id = searchParams.get(param);
    setSelectedIdState(id);
  }, [searchParams, param]);

  const setSelectedId = useCallback(
    (id: string | null) => {
      setSelectedIdState(id);
      const params = new URLSearchParams(searchParams.toString());
      if (id) {
        params.set(param, id);
      } else {
        params.delete(param);
      }
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : "?", { scroll: false });
    },
    [router, searchParams, param],
  );

  return [selectedId, setSelectedId] as const;
}

export function workspaceHref(params: {
  alertId?: string;
  offenseId?: string;
  incidentId?: string;
}): string {
  const qs = new URLSearchParams();
  if (params.alertId) qs.set("alert", params.alertId);
  if (params.offenseId) qs.set("offense", params.offenseId);
  if (params.incidentId) qs.set("incident", params.incidentId);
  return `/investigation?${qs.toString()}`;
}
