"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { FileText, Server, ShieldAlert, ShieldCheck } from "lucide-react";
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
  const [reportType, setReportType] = useState<"daily" | "weekly" | "monthly">("weekly");
  const [complianceFramework, setComplianceFramework] = useState<"soc2" | "iso27001">("soc2");

  const { data: templates } = useQuery({
    queryKey: ["reports", "compliance-templates"],
    queryFn: () => api<{ id: string; name: string; control_count: number }[]>("/api/v1/reports/compliance/templates"),
    staleTime: 300_000,
  });

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["reports", "summary"],
    queryFn: () => api<Summary>("/api/v1/reports/summary"),
    staleTime: 60_000,
  });

  const exportMutation = useMutation({
    mutationFn: async ({
      format,
      executive,
      compliance,
    }: {
      format: "csv" | "pdf";
      executive?: boolean;
      compliance?: boolean;
    }) => {
      let path: string;
      let name: string;
      if (compliance) {
        path = `/api/v1/reports/compliance?framework=${complianceFramework}&report_type=${reportType}&format=pdf`;
        name = `securi_compliance_${complianceFramework}_${reportType}.pdf`;
      } else if (executive) {
        path = `/api/v1/reports/executive?report_type=${reportType}&format=pdf`;
        name = `securi_executive_${reportType}.pdf`;
      } else {
        path = `/api/v1/reports/generate?report_type=${reportType}&format=${format}`;
        name = `securi_${reportType}_report.${format}`;
      }
      await downloadAuthenticated(path, name);
    },
    onSuccess: () => toast("success", "Report downloaded"),
    onError: (e: Error) => toast("error", "Export failed", e.message),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security Reports"
        subtitle="Executive PDFs for leadership plus operational daily, weekly, and monthly exports"
      />
      {isError ? (
        <QueryError onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton rows={4} />
      ) : data && data.total_hosts === 0 && data.open_alerts === 0 ? (
        <EmptyState
          title="No data for reports yet"
          description="Add hosts or run an Attack Lab simulation to populate report summaries."
          icon={<FileText className="w-10 h-10 opacity-40" />}
          action="/simulation"
          actionLabel="Open Attack Lab"
        />
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
      <Panel title="Executive PDF" subtitle="KPIs, MITRE, UEBA status, and recommendations for leadership">
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
          <Button
            type="button"
            onClick={() => exportMutation.mutate({ format: "pdf", executive: true })}
            loading={exportMutation.isPending}
          >
            <FileText className="w-4 h-4" />
            Download executive PDF
          </Button>
        </div>
      </Panel>
      <Panel title="Compliance assessment" subtitle="SOC 2 and ISO 27001 control mapping with live platform evidence">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 max-w-2xl">
            <Select
              label="Framework"
              value={complianceFramework}
              onChange={(e) => setComplianceFramework(e.target.value as typeof complianceFramework)}
            >
              {(templates ?? [
                { id: "soc2", name: "SOC 2 Type II", control_count: 8 },
                { id: "iso27001", name: "ISO/IEC 27001:2022", control_count: 7 },
              ]).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.control_count} controls)
                </option>
              ))}
            </Select>
            <Select
              label="Assessment period"
              value={reportType}
              onChange={(e) => setReportType(e.target.value as typeof reportType)}
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </Select>
          </div>
          <Button
            type="button"
            variant="ghost"
            onClick={() => exportMutation.mutate({ format: "pdf", compliance: true })}
            loading={exportMutation.isPending}
          >
            <ShieldCheck className="w-4 h-4" />
            Download compliance PDF
          </Button>
        </div>
      </Panel>
      <Panel title="Operational export">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => exportMutation.mutate({ format: "pdf" })}
              loading={exportMutation.isPending}
              size="sm"
            >
              Export PDF
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => exportMutation.mutate({ format: "csv" })}
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
            Auto-generated recommendations for leadership action items
          </li>
        </ul>
      </Panel>
    </div>
  );
}
