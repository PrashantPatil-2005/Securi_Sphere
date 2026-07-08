"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, TrendingDown } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { Button } from "@/components/ui/Button";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { track } from "@/lib/telemetry";

interface FeedbackInsight {
  rule_id: string;
  rule_name: string;
  rule_type: string;
  enabled: boolean;
  false_positive_count: number;
  true_positive_count: number;
  feedback_total: number;
  false_positive_rate: number;
  recommendation: string;
}

const RECOMMENDATION_COPY: Record<string, { tone: "calm" | "urgency" | "confidence"; title: string }> = {
  healthy: { tone: "confidence", title: "Performing well" },
  consider_threshold_increase: { tone: "calm", title: "Consider raising threshold" },
  consider_disabling_or_refining: { tone: "urgency", title: "High false-positive rate" },
};

export function RuleFeedbackInsights() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["alert-rules", "feedback-insights"],
    queryFn: () => api<{ items: FeedbackInsight[] }>("/api/v1/alert-rules/feedback-insights"),
    staleTime: 60_000,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api(`/api/v1/alert-rules/${id}`, { method: "PATCH", body: JSON.stringify({ enabled: !enabled }) }),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
      queryClient.invalidateQueries({ queryKey: ["alert-rules", "feedback-insights"] });
      track("rule_tuning_action", { rule_id: vars.id, action: vars.enabled ? "disable" : "enable" });
      toast("success", "Rule updated");
    },
    onError: (e: Error) => toast("error", "Update failed", e.message),
  });

  const items = (data?.items ?? []).filter((i) => i.feedback_total >= 3);
  const noisy = items.filter((i) => i.recommendation !== "healthy");

  if (isLoading) return <TableSkeleton rows={3} />;

  if (!items.length) {
    return (
      <Panel title="Rule tuning insights" subtitle="Based on analyst feedback">
        <EmptyState
          title="Not enough feedback yet"
          description="Mark alerts as false or true positive during triage to unlock tuning recommendations."
        />
      </Panel>
    );
  }

  return (
    <Panel title="Rule tuning insights" subtitle={`${noisy.length} rule(s) may need attention`}>
      {noisy.length > 0 && (
        <EmotionBanner
          tone="urgency"
          title="False positives are costing analyst time"
          message="Review noisy rules below. Consider disabling or refining rules with high FP rates."
          className="mb-4"
        />
      )}
      <div className="space-y-3">
        {items.slice(0, 8).map((item) => {
          const rec = RECOMMENDATION_COPY[item.recommendation] ?? RECOMMENDATION_COPY.healthy;
          const fpPct = Math.round(item.false_positive_rate * 100);
          return (
            <div key={item.rule_id} className="glass-panel p-3 space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-sm">{item.rule_name}</p>
                  <p className="text-xs text-muted">{item.rule_type} · {item.feedback_total} feedback labels</p>
                </div>
                <span className={`text-xs font-medium emotion-${rec.tone} px-2 py-0.5 rounded border`}>
                  {rec.title}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted">
                <span className="inline-flex items-center gap-1">
                  <TrendingDown className="w-3 h-3" />
                  FP rate {fpPct}%
                </span>
                <span>FP {item.false_positive_count} / TP {item.true_positive_count}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link href={`/alerts?rule_type=${item.rule_type}`} className="btn-ghost text-xs">
                  View alerts
                </Link>
                {item.recommendation !== "healthy" && (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="text-xs"
                    onClick={() => toggleMutation.mutate({ id: item.rule_id, enabled: item.enabled })}
                  >
                    <AlertTriangle className="w-3 h-3" />
                    {item.enabled ? "Disable rule" : "Re-enable rule"}
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
