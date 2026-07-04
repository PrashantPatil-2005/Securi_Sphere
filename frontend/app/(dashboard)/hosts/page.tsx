"use client";

import { memo, useCallback, useMemo, useState } from "react";
import { Copy, Check, Info } from "lucide-react";
import { usePaginatedResource } from "@/lib/hooks/useApiQuery";
import { useDebounce } from "@/lib/hooks/useDebounce";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { rowKeyById } from "@/lib/rowKey";
import ExportMenu from "@/components/ExportMenu";
import PaginationBar from "@/components/PaginationBar";
import SortSelect from "@/components/SortSelect";
import { VirtualDataTable, type Column } from "@/components/VirtualDataTable";
import { PageHeader, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { HostRiskDrawer } from "@/components/HostRiskDrawer";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { useUser } from "@/lib/hooks/useUser";

interface Host {
  id: string;
  name: string;
  hostname: string | null;
  status: string;
  enrolled: boolean;
  os_info: string | null;
  last_seen: string | null;
  risk_score: number | null;
  alert_count: number | null;
}

interface EnrollmentModal {
  token: string;
  install_command: string;
  expires_at: string;
  host_name: string;
}

const statusTone: Record<string, string> = {
  online: "text-[var(--success)]",
  inactive: "text-[var(--muted)]",
  offline: "text-[var(--muted)]",
  warning: "text-[var(--warning)]",
  critical: "text-[var(--danger)]",
};

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const { toast } = useToast();

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast("success", "Copied", label);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast("error", "Copy failed", "Select and copy manually");
    }
  }

  return (
    <button type="button" onClick={copy} className="btn-ghost text-xs shrink-0" aria-label={`Copy ${label}`}>
      {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

const HostActions = memo(function HostActions({ host, onEnroll }: { host: Host; onEnroll: (h: Host) => void }) {
  if (host.enrolled && host.status === "online") {
    return <span className="text-xs text-muted">Enrolled</span>;
  }
  return (
    <button onClick={() => onEnroll(host)} className="btn-ghost text-xs">
      {host.enrolled ? "Re-enroll" : "Enroll"}
    </button>
  );
});

export default function HostsPage() {
  const { toast } = useToast();
  const { data: user } = useUser();
  const canManageHosts = user?.role?.name === "admin" || user?.role?.name === "analyst";
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sort, setSort] = useState("newest");
  const [filters, setFilters] = useState({ hostname: "", status: "", os_info: "", min_risk: "", max_risk: "" });
  const debouncedHostname = useDebounce(filters.hostname, 400);
  const queryFilters = useMemo(
    () => ({
      ...filters,
      hostname: debouncedHostname,
      min_risk: filters.min_risk || undefined,
      max_risk: filters.max_risk || undefined,
    }),
    [filters, debouncedHostname],
  );
  const [enrollment, setEnrollment] = useState<EnrollmentModal | null>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [newName, setNewName] = useState("");
  const [riskHostId, setRiskHostId] = useState<string | null>(null);

  const { data, isLoading, isFetching, isError, refetch } = usePaginatedResource<Host>({
    endpoint: "/api/v1/hosts",
    queryKey: "hosts",
    page,
    pageSize,
    sort,
    filters: queryFilters,
    includeTimeRange: false,
  });

  const enroll = useCallback(async (host: Host) => {
    setEnrolling(true);
    try {
      const token = await api<EnrollmentModal>(`/api/v1/hosts/${host.id}/enrollment-token`, { method: "POST" });
      setEnrollment({ ...token, host_name: host.name });
    } catch (e) {
      toast("error", "Enrollment failed", e instanceof Error ? e.message : "Could not create token");
    } finally {
      setEnrolling(false);
    }
  }, [toast]);

  const columns: Column<Host>[] = useMemo(
    () => [
      { key: "name", header: "Host", width: "130px", render: (h) => (
        <button type="button" className="font-medium text-left hover:text-accent" onClick={() => setRiskHostId(h.id)}>
          {h.name}
        </button>
      ) },
      {
        key: "enrolled",
        header: "Agent",
        width: "90px",
        render: (h) => (
          <span className={`text-xs ${h.enrolled ? "text-[var(--success)]" : "text-muted"}`}>
            {h.enrolled ? "Enrolled" : "Pending"}
          </span>
        ),
      },
      {
        key: "hostname",
        header: "Hostname",
        width: "120px",
        render: (h) => <span className="text-xs text-muted truncate">{h.hostname ?? "—"}</span>,
      },
      {
        key: "status",
        header: "Status",
        width: "80px",
        render: (h) => <span className={`capitalize text-xs ${statusTone[h.status] || ""}`}>{h.status}</span>,
      },
      {
        key: "risk",
        header: "Risk",
        width: "60px",
        render: (h) => <span className="tabular-nums text-[var(--danger)]">{h.risk_score ?? "—"}</span>,
      },
      {
        key: "alerts",
        header: "Alerts",
        width: "60px",
        render: (h) => <span className="tabular-nums">{h.alert_count ?? 0}</span>,
      },
      {
        key: "seen",
        header: "Last seen",
        width: "150px",
        render: (h) => (
          <span className="text-[var(--muted)] text-xs tabular-nums">
            {h.last_seen ? new Date(h.last_seen).toLocaleString() : "—"}
          </span>
        ),
      },
      {
        key: "actions",
        header: "",
        width: "90px",
        render: (h) => <HostActions host={h} onEnroll={enroll} />,
      },
    ],
    [enroll],
  );

  async function addHost(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/v1/hosts", { method: "POST", body: JSON.stringify({ name: newName }) });
      setNewName("");
      refetch();
      toast("success", "Host added", "Generate an enrollment token to install the agent.");
    } catch (err) {
      toast("error", "Failed to add host", err instanceof Error ? err.message : "Unknown error");
    }
  }

  return (
    <div>
      <PageHeader title="Hosts" subtitle="Register endpoints, enroll agents, and monitor connectivity" action={canManageHosts ? <ExportMenu resource="hosts" query={buildQuery({ sort, ...queryFilters }, {})} /> : undefined} />
      {!canManageHosts && (
        <div className="mb-4 px-4 py-3 rounded-lg border border-warning/30 bg-warning/10 text-body text-sm">
          Your account is <strong className="capitalize">{user?.role?.name ?? "viewer"}</strong> — only <strong>admin</strong> or <strong>analyst</strong> can add hosts.
          See <a href="/profile" className="text-accent underline">Profile</a> for your role.
        </div>
      )}
      <ol className="text-caption normal-case text-muted mb-4 list-decimal list-inside space-y-1">
        <li>Add a host (status: inactive)</li>
        <li>Click Enroll → run install command on Ubuntu/Debian VM</li>
        <li>Agent registers → status becomes online; heartbeats keep it live</li>
      </ol>
      <form onSubmit={addHost} className="flex gap-2 mb-4">
        <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="New host name" required className="input-siem max-w-xs" disabled={!canManageHosts} />
        <button type="submit" className="btn-primary" disabled={!canManageHosts}>Add host</button>
      </form>
      <div className="filter-bar">
        <input placeholder="Hostname" value={filters.hostname} onChange={(e) => { setFilters({ ...filters, hostname: e.target.value }); setPage(1); }} className="input-siem" />
        <select value={filters.status} onChange={(e) => { setFilters({ ...filters, status: e.target.value }); setPage(1); }} className="input-siem">
          <option value="">All statuses</option>
          {["inactive", "online", "offline", "warning", "critical"].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <SortSelect value={sort} onChange={(s) => { setSort(s); setPage(1); }} />
      </div>
      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <QueryError onRetry={() => refetch()} />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState title="No hosts" description="Add a host, then enroll a Debian or Ubuntu VM with the install command below." />
      ) : (
        <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
          <VirtualDataTable rows={data?.items ?? []} columns={columns} rowKey={rowKeyById} />
        </div>
      )}
      <PaginationBar page={page} pageSize={pageSize} total={data?.total ?? 0} onPage={setPage} onPageSize={(s) => { setPageSize(s); setPage(1); }} />
      <HostRiskDrawer hostId={riskHostId} onClose={() => setRiskHostId(null)} />
      {enrollment && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-4 z-50" onClick={() => setEnrollment(null)}>
          <div className="panel max-w-2xl w-full p-5 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div>
              <h2 className="text-subheading">Install agent on {enrollment.host_name}</h2>
              <p className="text-caption normal-case text-muted mt-1">
                Token expires {new Date(enrollment.expires_at).toLocaleString()}.
              </p>
            </div>
            <div className="rounded-lg border border-accent/25 bg-accent/5 p-4 space-y-3">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-accent shrink-0 mt-0.5" aria-hidden />
                <div className="space-y-2 text-caption normal-case text-muted">
                  <p className="text-body font-medium text-foreground">Platform requirements</p>
                  <ul className="list-disc pl-4 space-y-1">
                    <li><strong className="text-foreground font-medium">Supported:</strong> Ubuntu, Debian, or Kali Linux (apt-based)</li>
                    <li><strong className="text-foreground font-medium">Run as:</strong> root (<code className="text-xs">sudo</code>)</li>
                    <li><strong className="text-foreground font-medium">Needs:</strong> Python 3, systemd, outbound access to this server</li>
                    <li><strong className="text-foreground font-medium">Not supported:</strong> Windows, macOS, RHEL/CentOS (no apt)</li>
                  </ul>
                  <p>Collects <code className="text-xs">/var/log/auth.log</code>, syslog, and host metrics (CPU, memory, disk).</p>
                </div>
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between gap-2 mb-1">
                <p className="text-xs font-medium text-muted uppercase tracking-wide">Install command</p>
                <CopyButton text={enrollment.install_command} label="Install command" />
              </div>
              <code className="block text-xs break-all bg-[var(--input-bg)] p-3 rounded font-mono border border-border-subtle">
                {enrollment.install_command}
              </code>
            </div>
            <div>
              <div className="flex items-center justify-between gap-2 mb-1">
                <p className="text-xs font-medium text-muted uppercase tracking-wide">Enrollment token</p>
                <CopyButton text={enrollment.token} label="Enrollment token" />
              </div>
              <code className="block text-xs break-all font-mono text-muted">{enrollment.token}</code>
            </div>
            <p className="text-caption normal-case text-muted">
              Run the install command on the target VM. Within ~30 seconds the host should show <strong>Enrolled</strong> and status <strong>online</strong>.
              See <code className="text-xs">docs/AGENT_INSTALL.md</code> for troubleshooting.
            </p>
            <Button onClick={() => { setEnrollment(null); refetch(); }}>Done</Button>
          </div>
        </div>
      )}
      {enrolling && (
        <div className="fixed inset-0 bg-black/30 z-40" aria-hidden />
      )}
    </div>
  );
}
