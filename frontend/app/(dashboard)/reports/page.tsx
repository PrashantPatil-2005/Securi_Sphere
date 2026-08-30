"use client";

import { Suspense, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { FileText, Server, ShieldAlert, ShieldCheck, Download } from "lucide-react";
import { api } from "@/lib/api";
import { downloadAuthenticated } from "@/lib/download";
import { PageHeader } from "@/components/ui/Panel";
import { Card, CardHeader } from "@/components/design-system/Card";
import { Button } from "@/components/design-system/Button";
import { Select } from "@/components/design-system/Select";
import { LoadingState } from "@/components/design-system/LoadingState";
import { QueryError } from "@/components/ui/QueryError";
import { EmptyState } from "@/components/design-system/EmptyState";
import { useToast } from "@/components/ui/Toast";

interface Summary {
  total_hosts: number;
  open_alerts: number;
  threat_scores: { host_id: string; score: number }[];
}

function ReportsPageContent() {
  const { toast } = useToast();
  const [reportType, setReportType] = useState<"daily" | "weekly" | "monthly">("weekly");
  const [complianceFramework, setComplianceFramework] = useState<"soc2" | "iso27001">("soc2");

  const { data: templates } = useQuery({
    queryKey: ["reports", "compliance-templates"],
    queryFn: () =>
      api<{ id: string; name: string; control_count: number }[]>(
        "/api/v1/reports/compliance/templates",
      ),
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

      {isError && <QueryError onRetry={() => refetch()} />}

      {isLoading && <LoadingState rows={4} />}

      {!isLoading && !isError && data && data.total_hosts === 0 && data.open_alerts === 0 && (
        <EmptyState
          title="No data for reports yet"
          description="Add hosts or run an Attack Lab simulation to populate report summaries."
          icon={<FileText className="w-10 h-10 opacity-40" />}
          action="/simulation"
          actionLabel="Open Attack Lab"
        />
      )}

      {/* Summary cards */}
      {data && (
        <div className="grid md:grid-cols-3 gap-4">
          <Card>
            <div className="p-4 text-center">
              <p className="text-2xl font-semibold tabular-nums text-accent">{data.total_hosts}</p>
              <p className="text-xs text-muted mt-1">Total hosts</p>
            </div>
          </Card>
          <Card>
            <div className="p-4 text-center">
              <p className="text-2xl font-semibold tabular-nums text-warning">{data.open_alerts}</p>
              <p className="text-xs text-muted mt-1">Open alerts</p>
            </div>
          </Card>
          <Card>
            <div className="p-4 text-center">
              <p className="text-2xl font-semibold tabular-nums text-foreground">{data.threat_scores.length}</p>
              <p className="text-xs text-muted mt-1">Hosts scored</p>
            </div>
          </Card>
        </div>
      )}

      {/* Executive PDF */}
      <Card>
        <CardHeader
          title="Executive PDF"
          subtitle="KPIs, MITRE, UEBA status, and recommendations for leadership"
        />
        <div className="p-4 space-y-4">
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
            <Download className="w-4 h-4" />
            Download executive PDF
          </Button>
        </div>
      </Card>

      {/* Compliance */}
      <Card>
        <CardHeader
          title="Compliance Assessment"
          subtitle="SOC 2 and ISO 27001 control mapping with live platform evidence"
        />
        <div className="p-4 space-y-4">
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
      </Card>

      {/* Operational export */}
      <Card>
        <CardHeader title="Operational Export" subtitle="Generate JSON, CSV, or PDF reports for the selected period" />
        <div className="p-4">
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => exportMutation.mutate({ format: "pdf" })}
              loading={exportMutation.isPending}
              size="sm"
            >
              <FileText className="w-4 h-4" />
              Export PDF
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => exportMutation.mutate({ format: "csv" })}
              disabled={exportMutation.isPending}
              size="sm"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </Button>
          </div>
        </div>
      </Card>

      {/* What's included */}
      <Card>
        <CardHeader title="What's Included" subtitle="Each generated report bundles" />
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-3 text-sm">
            <Server className="w-4 h-4 text-accent shrink-0" />
            <span>Host inventory and connectivity summary</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <ShieldAlert className="w-4 h-4 text-warning shrink-0" />
            <span>Open and resolved alerts for the period</span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <FileText className="w-4 h-4 text-muted shrink-0" />
            <span>Auto-generated recommendations for leadership action items</span>
          </div>
        </div>
      </Card>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<LoadingState rows={4} />}>
      <ReportsPageContent />
    </Suspense>
  );
}
