"use client";

import { Suspense, useState } from "react";
import dynamic from "next/dynamic";
import { Target } from "lucide-react";
import { PageHeader } from "@/components/ui/Panel";
import { Card, CardHeader } from "@/components/design-system/Card";
import { QueryError } from "@/components/ui/QueryError";
import { LoadingState } from "@/components/design-system/LoadingState";
import { EmptyState } from "@/components/design-system/EmptyState";
import { useMitreMatrix, useMitreDrilldown } from "@/lib/hooks/useMitre";
import { MitreMatrix } from "@/components/mitre/MitreMatrix";
import { MitreDrilldown } from "@/components/mitre/MitreDrilldown";
import { useTimeRange } from "@/lib/timeRange";

const LazyBarChart = dynamic(
  () =>
    import("recharts").then((mod) => {
      const { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } = mod;
      return function LazyBarChartWrapper({ data }: { data: { name: string; coverage: number }[] }) {
        return (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#7b8ba3" }} />
              <YAxis domain={[0, 100]} stroke="#7b8ba3" />
              <Tooltip contentStyle={{ background: "#111820", border: "1px solid #243044" }} />
              <Bar dataKey="coverage" fill="var(--accent)" isAnimationActive={false} name="Coverage %" />
            </BarChart>
          </ResponsiveContainer>
        );
      };
    }),
  { loading: () => <div className="h-[220px] skeleton rounded" />, ssr: false },
);

function MitrePageContent() {
  const { queryParams } = useTimeRange();
  const [selectedTechnique, setSelectedTechnique] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useMitreMatrix({
    preset: queryParams.preset,
    fromTime: queryParams.from_time,
    toTime: queryParams.to_time,
  });

  const { data: drilldownData, isLoading: drilldownLoading } = useMitreDrilldown(selectedTechnique, {
    preset: queryParams.preset,
    fromTime: queryParams.from_time,
    toTime: queryParams.to_time,
  });

  const chartData = Object.entries(data?.tactic_coverage ?? {}).map(([tactic, pct]) => ({
    name: tactic.length > 12 ? tactic.slice(0, 12) + "…" : tactic,
    coverage: pct,
  }));

  const totalHits = Object.values(data?.tactics ?? {}).flat().reduce((sum, t) => sum + t.count, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="MITRE ATT&CK"
        subtitle="Detection coverage heatmap — click a technique to drill down"
      />

      {isLoading && <LoadingState rows={6} />}
      {isError && <QueryError onRetry={() => refetch()} />}

      {data && (
        <>
          {/* Summary cards */}
          <div className="grid md:grid-cols-3 gap-4">
            <Card className="text-center">
              <div className="p-4">
                <p className="text-3xl font-semibold tabular-nums text-accent">{data.coverage_pct}%</p>
                <p className="text-xs text-muted mt-1">Overall coverage</p>
              </div>
            </Card>
            <Card className="text-center">
              <div className="p-4">
                <p className="text-3xl font-semibold tabular-nums text-foreground">{data.total_techniques}</p>
                <p className="text-xs text-muted mt-1">Techniques seeded</p>
              </div>
            </Card>
            <Card className="text-center">
              <div className="p-4">
                <p className="text-3xl font-semibold tabular-nums text-danger">{totalHits}</p>
                <p className="text-xs text-muted mt-1">Total event matches</p>
              </div>
            </Card>
          </div>

          {/* Coverage chart */}
          {chartData.length > 0 && (
            <Card>
              <CardHeader title="Coverage by tactic" />
              <div className="p-4">
                <LazyBarChart data={chartData} />
              </div>
            </Card>
          )}

          {totalHits === 0 && (
            <EmptyState
              title="No technique matches in range"
              description="Run Attack Lab or ingest events with MITRE mappings to populate the heatmap."
              icon={<Target className="w-10 h-10 opacity-40" />}
            />
          )}

          {/* Matrix */}
          <MitreMatrix
            tactics={data.tactics}
            tacticCoverage={data.tactic_coverage}
            selectedTechnique={selectedTechnique}
            onSelect={setSelectedTechnique}
          />

          {/* Drilldown */}
          <MitreDrilldown
            data={drilldownData}
            isLoading={drilldownLoading}
            onClose={() => setSelectedTechnique(null)}
          />
        </>
      )}
    </div>
  );
}

export default function MitrePage() {
  return (
    <Suspense fallback={<LoadingState rows={6} />}>
      <MitrePageContent />
    </Suspense>
  );
}
