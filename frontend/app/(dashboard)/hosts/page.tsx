"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { useHostList, useHostCreateMutation } from "@/lib/hooks/useHosts";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { buildQuery } from "@/lib/buildQuery";
import ExportMenu from "@/components/export/ExportMenu";
import PaginationBar from "@/components/pagination/PaginationBar";
import { PageHeader } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useUser } from "@/lib/hooks/useUser";
import { HostFiltersBar } from "@/components/hosts/HostFilters";
import { HostRow } from "@/components/hosts/HostRow";
import { HostEmptyState } from "@/components/hosts/HostEmptyState";
import { DEFAULT_HOST_FILTERS } from "@/lib/types/host";
import type { HostFilters, HostSummary } from "@/lib/types/host";

export default function HostsPage() {
  return (
    <Suspense fallback={<TableSkeleton />}>
      <HostsPageContent />
    </Suspense>
  );
}

function HostsPageContent() {
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const { data: user } = useUser();
  const canManageHosts = user?.role?.name === "admin" || user?.role?.name === "analyst";

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [filters, setFilters] = useState<HostFilters>(DEFAULT_HOST_FILTERS);
  const [selectedHost, setSelectedHost] = useState<HostSummary | null>(null);
  const [showAddHost, setShowAddHost] = useState(false);
  const [newHostName, setNewHostName] = useState("");

  // Read URL params on mount
  useEffect(() => {
    const status = searchParams.get("status");
    if (status) {
      setFilters((prev) => ({ ...prev, status }));
    }
  }, [searchParams]);

  // Debounce search
  const debouncedHostname = useDebounce(filters.hostname, 400);
  const debouncedFilters = useMemo(
    () => ({ ...filters, hostname: debouncedHostname }),
    [filters, debouncedHostname],
  );

  const {
    data,
    isLoading,
    isFetching,
    isError,
    refetch,
  } = useHostList({
    page,
    pageSize,
    sort,
    filters: debouncedFilters,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const createMutation = useHostCreateMutation({
    onSuccess: () => {
      toast("success", "Host added", "Generate an enrollment token to install the agent.");
      setShowAddHost(false);
      setNewHostName("");
      refetch();
    },
    onError: (e) => {
      toast("error", "Failed to add host", e.message);
    },
  });

  const exportQuery = buildQuery({ sort, ...debouncedFilters }, {});

  const handleClearFilters = useCallback(() => {
    setFilters(DEFAULT_HOST_FILTERS);
    setPage(1);
  }, []);

  const handleSelectHost = useCallback((host: HostSummary) => {
    setSelectedHost(host);
  }, []);

  const handleAddHost = useCallback(() => {
    if (!newHostName.trim()) return;
    createMutation.mutate({ name: newHostName.trim() });
  }, [newHostName, createMutation]);

  return (
    <div>
      <PageHeader
        title="Hosts"
        subtitle="Monitored systems and security assets"
        action={
          <div className="flex items-center gap-2">
            {canManageHosts && (
              <Button variant="primary" size="sm" onClick={() => setShowAddHost(true)}>
                Add Host
              </Button>
            )}
            <ExportMenu resource="hosts" query={exportQuery} />
          </div>
        }
      />

      <div className="mt-4">
        <HostFiltersBar
          filters={filters}
          sort={sort}
          onFiltersChange={(f) => { setFilters(f); setPage(1); }}
          onSortChange={(s) => { setSort(s); setPage(1); }}
          total={total}
        />
      </div>

      <div className="mt-4">
        {isLoading ? (
          <TableSkeleton rows={12} />
        ) : isError ? (
          <QueryError onRetry={() => refetch()} />
        ) : items.length === 0 ? (
          <HostEmptyState
            hasFilters={Object.values(debouncedFilters).some(Boolean)}
            onClear={handleClearFilters}
          />
        ) : (
          <>
            <div className={`transition-opacity ${isFetching ? "opacity-70" : ""}`}>
              {/* Desktop table header */}
              <div className="hidden md:flex items-center gap-3 px-3 py-2 border-b border-border-subtle text-[11px] font-medium text-muted uppercase tracking-wide">
                <span className="w-2 shrink-0" />
                <span className="flex-1">Host</span>
                <span className="w-20 text-right">Status</span>
                <span className="w-10 text-right">Risk</span>
                <span className="w-16 text-right">Agent</span>
                <span className="w-10 text-right">Alerts</span>
                <span className="w-20 text-right hidden md:block">Last Seen</span>
              </div>

              {/* Host rows */}
              <div>
                {items.map((host) => (
                  <HostRow
                    key={host.id}
                    host={host}
                    selected={selectedHost?.id === host.id}
                    onClick={handleSelectHost}
                  />
                ))}
              </div>
            </div>

            {/* Pagination */}
            <div className="mt-4">
              <PaginationBar
                page={page}
                pageSize={pageSize}
                total={total}
                onPage={setPage}
                onPageSize={(s) => { setPageSize(s); setPage(1); }}
              />
            </div>
          </>
        )}
      </div>

      {/* Add Host Dialog */}
      <Dialog
        open={showAddHost}
        onClose={() => { setShowAddHost(false); setNewHostName(""); }}
        title="Add Host"
        description="Create a new host entry to generate an enrollment token."
      >
        <div className="space-y-4">
          <Input
            label="Host name"
            value={newHostName}
            onChange={(e) => setNewHostName(e.target.value)}
            placeholder="e.g. server-prod-03"
            required
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => { setShowAddHost(false); setNewHostName(""); }}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleAddHost}
              disabled={!newHostName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? "Adding..." : "Add Host"}
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
