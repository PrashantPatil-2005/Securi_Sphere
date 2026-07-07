"use client";

import { Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buildQuery } from "@/lib/buildQuery";
import { useTimeRange } from "@/lib/timeRange";
import { useDeepLinkedSelection } from "@/lib/hooks/useDeepLinkedSelection";
import TimeRangeBar from "@/components/TimeRangeBar";
import { MitreTechniqueDrilldown } from "@/components/mitre/MitreTechniqueDrilldown";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { PageHeader, EmptyState } from "@/components/ui/Panel";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { CHART_THEME, axisProps } from "@/lib/design/chartTheme";

interface Technique {
  technique_id: string;
  tactic: string;
  name: string;
  count: number;
}

const TACTIC_ORDER = [
  "Initial Access", "Execution", "Persistence", "Privilege Escalation",
  "Defense Evasion", "Discovery", "Lateral Movement", "Credential Access", "Impact",
];

interface MatrixResponse {
  tactics: Record<string, Technique[]>;
  coverage_pct: number;
  tactic_coverage: Record<string, number>;
  total_techniques: number;
}

function heatClass(count: number, selected: boolean) {
  const base = count > 5
    ? "bg-danger/20 border-danger/40"
    : count > 0
      ? "bg-warning/15 border-warning/30"
      : "glass-panel border-border-subtle";
  const ring = selected ? " ring-2 ring-accent ring-offset-1 ring-offset-background" : "";
  return `${base}${ring}`;
}

function MitrePageContent() {
  const { queryParams } = useTimeRange();
  const [selectedTechnique, setSelectedTechnique] = useDeepLinkedSelection("technique");
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["mitre-matrix", queryParams],
    queryFn: () => api<MatrixResponse>(`/api/v1/mitre/matrix${buildQuery({}, queryParams)}`),
  });

  const tactics = data?.tactics ?? {};
  const tacticOrder = TACTIC_ORDER.filter((t) => tactics[t]).concat(
    Object.keys(tactics).filter((t) => !TACTIC_ORDER.includes(t)),
  );
  const chartData = Object.entries(data?.tactic_coverage ?? {}).map(([tactic, pct]) => ({
    name: tactic.split(" ")[0],
    coverage: pct,
  }));
  const totalHits = Object.values(tactics).flat().reduce((sum, t) => sum + t.count, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="MITRE ATT&CK"
        subtitle="Detection coverage heatmap — click a technique to drill down"
      />
      <TimeRangeBar />
      {isLoading && <TableSkeleton rows={6} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {data && (
        <div className="grid md:grid-cols-3 gap-4">
          <GlassPanel className="text-center">
            <p className="text-3xl font-semibold tabular-nums text-accent">{data.coverage_pct}%</p>
            <p className="text-caption normal-case text-muted">Overall coverage</p>
          </GlassPanel>
          <GlassPanel className="text-center md:col-span-2">
            <p className="text-sm text-muted">
              {data.total_techniques} techniques seeded · heat intensity = event matches in range
            </p>
          </GlassPanel>
        </div>
      )}
      {chartData.length > 0 && (
        <GlassPanel>
          <h2 className="text-subheading mb-4">Coverage by tactic</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <XAxis dataKey="name" {...axisProps} tick={{ fontSize: 10 }} />
              <YAxis domain={[0, 100]} {...axisProps} />
              <Tooltip {...CHART_THEME.tooltip} />
              <Bar dataKey="coverage" fill={CHART_THEME.colors.primary} isAnimationActive={false} name="Coverage %" />
            </BarChart>
          </ResponsiveContainer>
        </GlassPanel>
      )}
      {data && totalHits === 0 && (
        <EmptyState
          title="No technique matches in range"
          description="Run Attack Lab or ingest events with MITRE mappings to populate the heatmap."
        />
      )}
      <div className="overflow-x-auto">
        <div className="flex gap-3 min-w-max pb-4">
          {tacticOrder.map((tactic) => {
            const items = tactics[tactic] || [];
            const cov = data?.tactic_coverage?.[tactic] ?? 0;
            return (
              <div key={tactic} className="w-48 shrink-0">
                <div className="glass-panel px-2 py-2 rounded-t text-xs font-semibold flex justify-between gap-1">
                  <span className="truncate">{tactic}</span>
                  <span className="text-accent tabular-nums">{cov}%</span>
                </div>
                <div className="border border-t-0 border-border-subtle rounded-b min-h-[120px] p-2 space-y-1 bg-glass/30">
                  {items.map((t) => {
                    const selected = selectedTechnique === t.technique_id;
                    return (
                      <button
                        key={t.technique_id}
                        type="button"
                        onClick={() => setSelectedTechnique(t.technique_id)}
                        className={`w-full text-left text-xs p-2 rounded border transition-colors hover:border-accent/50 cursor-pointer ${heatClass(t.count, selected)}`}
                        title={t.name}
                      >
                        <div className="font-mono text-muted">{t.technique_id}</div>
                        <div className="truncate">{t.name}</div>
                        {t.count > 0 && <div className="text-danger mt-1 tabular-nums">{t.count} events</div>}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <MitreTechniqueDrilldown
        techniqueId={selectedTechnique}
        queryParams={queryParams}
        onClose={() => setSelectedTechnique(null)}
      />
    </div>
  );
}

export default function MitrePage() {
  return (
    <Suspense fallback={<TableSkeleton rows={6} />}>
      <MitrePageContent />
    </Suspense>
  );
}
