"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { useHostList, useHostCreateMutation, useEnrollmentTokenMutation } from "@/lib/hooks/useHosts";
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
  const [enrollmentResult, setEnrollmentResult] = useState<{
    token: string;
    install_command: string;
    host_name: string;
  } | null>(null);
  const createdHostIdRef = useRef<string | null>(null);

  useEffect(() => {
    const status = searchParams.get("status");
    if (status) {
      setFilters((prev) => ({ ...prev, status }));
    }
  }, [searchParams]);

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

  const enrollmentMutation = useEnrollmentTokenMutation({
    onSuccess: (data) => {
      setEnrollmentResult({
        token: data.token,
        install_command: data.install_command,
        host_name: data.host_name,
      });
      setShowAddHost(false);
      setNewHostName("");
      refetch();
    },
    onError: (e) => {
      toast("error", "Failed to generate enrollment token", e.message);
      setShowAddHost(false);
      setNewHostName("");
      refetch();
    },
  });

  const createMutation = useHostCreateMutation({
    onSuccess: (data: any) => {
      const hostId = data?.id;
      if (hostId) {
        createdHostIdRef.current = hostId;
        enrollmentMutation.mutate(hostId);
      } else {
        toast("success", "Host added", "Navigate to the host to generate an enrollment token.");
        setShowAddHost(false);
        setNewHostName("");
        refetch();
      }
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
              <div className="hidden md:flex items-center gap-3 px-3 py-2 border-b border-border-subtle text-[11px] font-medium text-muted uppercase tracking-wide">
                <span className="w-2 shrink-0" />
                <span className="flex-1">Host</span>
                <span className="w-20 text-right">Status</span>
                <span className="w-10 text-right">Risk</span>
                <span className="w-16 text-right">Agent</span>
                <span className="w-10 text-right">Alerts</span>
                <span className="w-20 text-right hidden md:block">Last Seen</span>
              </div>

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
              disabled={!newHostName.trim() || createMutation.isPending || enrollmentMutation.isPending}
            >
              {createMutation.isPending || enrollmentMutation.isPending ? "Creating..." : "Add Host"}
            </Button>
          </div>
        </div>
      </Dialog>

      {/* Enrollment Token Dialog */}
      <Dialog
        open={!!enrollmentResult}
        onClose={() => setEnrollmentResult(null)}
        title="Host Created — Enrollment Token"
        description="Copy this token and run the install command on the target host."
      >
        {enrollmentResult && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted block mb-1">Host</label>
              <p className="text-sm font-medium text-foreground">{enrollmentResult.host_name}</p>
            </div>
            <div>
              <label className="text-xs font-medium text-muted block mb-1">Enrollment Token</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs font-mono bg-card-elevated px-3 py-2 rounded border border-border-subtle break-all">
                  {enrollmentResult.token}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(enrollmentResult.token);
                    toast("success", "Copied", "Token copied to clipboard.");
                  }}
                >
                  Copy
                </Button>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted block mb-1">Install Command (Linux)</label>
              <div className="flex items-start gap-2">
                <pre className="flex-1 text-xs font-mono bg-card-elevated px-3 py-2 rounded border border-border-subtle overflow-x-auto whitespace-pre-wrap break-all">
                  {enrollmentResult.install_command}
                </pre>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(enrollmentResult.install_command);
                    toast("success", "Copied", "Install command copied to clipboard.");
                  }}
                >
                  Copy
                </Button>
              </div>
              <p className="text-[10px] text-muted mt-1">Run this on the target Linux host with sudo privileges.</p>
            </div>
            <div className="flex justify-end">
              <Button variant="primary" onClick={() => setEnrollmentResult(null)}>
                Done
              </Button>
            </div>
          </div>
        )}
      </Dialog>
    </div>
  );
}
