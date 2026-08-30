"use client";

import { Suspense, useCallback, useState } from "react";
import { FlaskConical } from "lucide-react";
import { PageHeader } from "@/components/ui/Panel";
import { Card } from "@/components/design-system/Card";
import { Button } from "@/components/design-system/Button";
import { Select } from "@/components/design-system/Select";
import { QueryError } from "@/components/ui/QueryError";
import { LoadingState } from "@/components/design-system/LoadingState";
import { useToast } from "@/components/ui/Toast";
import {
  useUebaSummary,
  useUebaAnomalies,
  useUebaScanMutation,
  useUebaUpdateMutation,
} from "@/lib/hooks/useUeba";
import { UebaSummaryCards } from "@/components/ueba/UebaSummaryCards";
import { UebaAnomalyList } from "@/components/ueba/UebaAnomalyList";
import { DEFAULT_UEBA_FILTERS } from "@/lib/types/ueba";
import type { UebaFilters } from "@/lib/types/ueba";

function UebaPageContent() {
  const { toast } = useToast();
  const [filters, setFilters] = useState<UebaFilters>(DEFAULT_UEBA_FILTERS);

  const { data: summary, isLoading: summaryLoading } = useUebaSummary();

  const { data: anomalies = [], isLoading, isError, refetch } = useUebaAnomalies({
    status: filters.status || undefined,
    severity: filters.severity || undefined,
    entityType: filters.entity_type || undefined,
    limit: 50,
  });

  const scanMutation = useUebaScanMutation();
  const updateMutation = useUebaUpdateMutation();

  const handleScan = useCallback(() => {
    scanMutation.mutate(undefined, {
      onSuccess: (res) => {
        toast("success", "UEBA scan complete", `${res.created} new, ${res.updated} updated`);
      },
      onError: (e: Error) => {
        toast("error", "Scan failed", e.message);
      },
    });
  }, [scanMutation, toast]);

  const handleDismiss = useCallback(
    (id: string) => {
      updateMutation.mutate(
        { id, status: "dismissed" },
        { onError: (e: Error) => toast("error", "Update failed", e.message) },
      );
    },
    [updateMutation, toast],
  );

  const handleResolve = useCallback(
    (id: string) => {
      updateMutation.mutate(
        { id, status: "resolved" },
        { onError: (e: Error) => toast("error", "Update failed", e.message) },
      );
    },
    [updateMutation, toast],
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="UEBA"
        subtitle="User & Entity Behavior Analytics — baseline deviations and anomaly detection"
        action={
          <Button
            size="sm"
            variant="ghost"
            loading={scanMutation.isPending}
            onClick={handleScan}
          >
            <FlaskConical className="w-4 h-4" />
            Run scan
          </Button>
        }
      />

      <UebaSummaryCards summary={summary} isLoading={summaryLoading} />

      {summary && (
        <Card>
          <div className="px-4 py-3 text-xs text-muted">
            Z-score ≥ {summary.z_threshold} · {summary.baseline_days}-day baseline ·{" "}
            {summary.enabled ? "Enabled" : "Disabled"}
          </div>
        </Card>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <Select
          value={filters.status}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          className="!w-auto !text-xs min-w-[110px]"
          aria-label="Filter by status"
        >
          <option value="">All status</option>
          <option value="open">Open</option>
          <option value="dismissed">Dismissed</option>
          <option value="resolved">Resolved</option>
        </Select>
        <Select
          value={filters.severity}
          onChange={(e) => setFilters((f) => ({ ...f, severity: e.target.value }))}
          className="!w-auto !text-xs min-w-[110px]"
          aria-label="Filter by severity"
        >
          <option value="">All severity</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </Select>
        <Select
          value={filters.entity_type}
          onChange={(e) => setFilters((f) => ({ ...f, entity_type: e.target.value }))}
          className="!w-auto !text-xs min-w-[110px]"
          aria-label="Filter by entity type"
        >
          <option value="">All entities</option>
          <option value="host">Hosts</option>
          <option value="user">Users</option>
        </Select>
      </div>

      {isError && <QueryError onRetry={() => refetch()} />}

      <UebaAnomalyList
        anomalies={anomalies}
        isLoading={isLoading}
        onDismiss={handleDismiss}
        onResolve={handleResolve}
      />
    </div>
  );
}

export default function UebaPage() {
  return (
    <Suspense fallback={<LoadingState rows={4} />}>
      <UebaPageContent />
    </Suspense>
  );
}
