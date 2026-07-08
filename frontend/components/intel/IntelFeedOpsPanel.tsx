"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Rss } from "lucide-react";
import { api } from "@/lib/api";
import { Panel, EmptyState } from "@/components/ui/Panel";
import { EmotionBanner } from "@/components/ui/EmotionState";
import { Button } from "@/components/ui/Button";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { track } from "@/lib/telemetry";

interface FeedSet {
  id: string;
  name: string;
  enabled: boolean;
  entry_count: number;
  source_type: string;
  feed_last_sync_at: string | null;
  feed_last_sync_status: string | null;
  feed_last_sync_error: string | null;
}

export function IntelFeedOpsPanel() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: sets = [], isLoading } = useQuery({
    queryKey: ["reference-sets"],
    queryFn: () => api<FeedSet[]>("/api/v1/reference-sets"),
  });

  const feedSets = sets.filter((s) => s.source_type === "feed");
  const failed = feedSets.filter((s) => s.feed_last_sync_status === "failed");
  const stale = feedSets.filter((s) => {
    if (!s.feed_last_sync_at) return true;
    const age = Date.now() - new Date(s.feed_last_sync_at).getTime();
    return age > 24 * 60 * 60 * 1000;
  });

  const bulkSync = useMutation({
    mutationFn: async () => {
      const targets = feedSets.filter((s) => s.enabled);
      await Promise.all(
        targets.map((s) => api(`/api/v1/reference-sets/${s.id}/sync-feed`, { method: "POST" })),
      );
      return targets.length;
    },
    onSuccess: (count) => {
      toast("success", `Synced ${count} feed(s)`);
      track("intel_feed_sync", { action: "bulk_sync", count });
      queryClient.invalidateQueries({ queryKey: ["reference-sets"] });
    },
    onError: (e: Error) => toast("error", "Bulk sync failed", e.message),
  });

  if (isLoading) return <TableSkeleton rows={3} />;

  if (!feedSets.length) {
    return (
      <Panel title="Threat intel feed operations" subtitle="Fleet sync health">
        <EmptyState title="No feed-backed sets" description="Create a reference set with an external feed URL to monitor sync health here." />
      </Panel>
    );
  }

  return (
    <Panel title="Threat intel feed operations" subtitle={`${feedSets.length} feed-backed set(s)`}>
      {(failed.length > 0 || stale.length > 0) && (
        <EmotionBanner
          tone={failed.length ? "urgency" : "calm"}
          title={failed.length ? `${failed.length} feed sync failure(s)` : `${stale.length} feed(s) may be stale`}
          message="Keep intel fresh to avoid missing indicators during detection."
          className="mb-4"
          action={
            <Button type="button" size="sm" loading={bulkSync.isPending} onClick={() => bulkSync.mutate()}>
              <RefreshCw className="w-3.5 h-3.5" />
              Sync all
            </Button>
          }
        />
      )}

      <div className="space-y-2">
        {feedSets.map((set) => (
          <div key={set.id} className="flex flex-wrap items-center justify-between gap-2 p-3 glass-panel text-sm">
            <div className="flex items-center gap-2 min-w-0">
              <Rss className="w-4 h-4 text-accent shrink-0" />
              <div className="min-w-0">
                <p className="font-medium truncate">{set.name}</p>
                <p className="text-xs text-muted">
                  {set.entry_count} entries
                  {set.feed_last_sync_at && ` · last sync ${new Date(set.feed_last_sync_at).toLocaleString()}`}
                </p>
                {set.feed_last_sync_error && (
                  <p className="text-xs text-danger truncate">{set.feed_last_sync_error}</p>
                )}
              </div>
            </div>
            <span
              className={
                set.feed_last_sync_status === "ok"
                  ? "text-success text-xs capitalize"
                  : set.feed_last_sync_status === "failed"
                    ? "text-danger text-xs capitalize"
                    : "text-muted text-xs"
              }
            >
              {set.feed_last_sync_status ?? "never synced"}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
