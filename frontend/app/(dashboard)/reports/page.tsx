"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { downloadAuthenticated } from "@/lib/download";
import { PageHeader, Panel, EmptyState } from "@/components/ui/Panel";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { QueryError } from "@/components/ui/QueryError";
import { useToast } from "@/components/ui/Toast";

interface Summary {
  total_hosts: number;
  open_alerts: number;
  threat_scores: { host_id: string; score: number }[];
}

export default function ReportsPage() {
  const { toast } = useToast();
  const [reportType, setReportType] = useState<"daily" | "weekly" | "monthly">("daily");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["reports", "summary"],
    queryFn: () => api<Summary>("/api/v1/reports/summary"),
    staleTime: 60_000,
  });

  const exportMutation = useMutation({
    mutationFn: async (format: "csv" | "pdf") => {
      await downloadAuthenticated(
        `/api/v1/reports/generate?report_type=${reportType}&format=${format}`,
        `securisphere_${reportType}_report.${format}`,
      );
    },
    onSuccess: () => toast("success", "Report downloaded"),
    onError: (e: Error) => toast("error", "Export failed", e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security Reports"
        subtitle="Daily, weekly, and monthly reports with events, alerts, risk scores, and MITRE mapping"
      />
      {isError ? (
        <QueryError onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton rows={4} />
      ) : data ? (
        <div className="grid md:grid-cols-3 gap-4">
          <div className="panel p-4">
            <p className="text-muted text-sm">Total Hosts</p>
            <p className="text-2xl font-bold tabular-nums">{data.total_hosts}</p>
          </div>
          <div className="panel p-4">
            <p className="text-muted text-sm">Open Alerts</p>
            <p className="text-2xl font-bold tabular-nums text-yellow-400">{data.open_alerts}</p>
          </div>
          <div className="panel p-4">
            <p className="text-muted text-sm">Hosts Scored</p>
            <p className="text-2xl font-bold tabular-nums">{data.threat_scores.length}</p>
          </div>
        </div>
      ) : (
        <EmptyState title="No summary data" description="Unable to load report summary." />
      )}
      <Panel title="Generate report">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3 items-center">
            <label className="text-sm text-muted">Report period</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value as typeof reportType)}
              className="input-siem"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => exportMutation.mutate("pdf")}
              disabled={exportMutation.isPending}
              className="btn-primary text-sm"
            >
              Export PDF
            </button>
            <button
              type="button"
              onClick={() => exportMutation.mutate("csv")}
              disabled={exportMutation.isPending}
              className="btn-ghost text-sm"
            >
              Export CSV
            </button>
          </div>
        </div>
      </Panel>
    </div>
  );
}
