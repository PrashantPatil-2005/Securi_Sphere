"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { FileText, Server, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { downloadAuthenticated } from "@/lib/download";
import { PageHeader, Panel, StatCard, EmptyState } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
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
          <StatCard label="Total hosts" value={data.total_hosts} tone="info" href="/hosts" />
          <StatCard label="Open alerts" value={data.open_alerts} tone="warning" href="/alerts" />
          <StatCard label="Hosts scored" value={data.threat_scores.length} tone="default" href="/analytics" />
        </div>
      ) : (
        <EmptyState
          title="No summary data"
          description="Unable to load report summary."
          icon={<FileText className="w-10 h-10 opacity-40" />}
        />
      )}
      <Panel title="Generate report">
        <div className="space-y-4">
          <Select
            label="Report period"
            value={reportType}
            onChange={(e) => setReportType(e.target.value as typeof reportType)}
            className="max-w-xs"
          >
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </Select>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              onClick={() => exportMutation.mutate("pdf")}
              loading={exportMutation.isPending}
              size="sm"
            >
              <FileText className="w-4 h-4" />
              Export PDF
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => exportMutation.mutate("csv")}
              disabled={exportMutation.isPending}
              size="sm"
            >
              Export CSV
            </Button>
          </div>
        </div>
      </Panel>
      <Panel title="What's included" subtitle="Each generated report bundles">
        <ul className="text-sm text-muted space-y-2 list-disc list-inside">
          <li className="flex items-center gap-2 list-none">
            <Server className="w-4 h-4 text-accent shrink-0" aria-hidden />
            Host inventory and connectivity summary
          </li>
          <li className="flex items-center gap-2 list-none">
            <ShieldAlert className="w-4 h-4 text-warning shrink-0" aria-hidden />
            Open and resolved alerts for the period
          </li>
          <li className="flex items-center gap-2 list-none">
            <FileText className="w-4 h-4 text-muted shrink-0" aria-hidden />
            Threat scores and MITRE technique mapping
          </li>
        </ul>
      </Panel>
    </div>
  );
}
