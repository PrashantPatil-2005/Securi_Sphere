"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, X } from "lucide-react";
import { api } from "@/lib/api";
import { widgetLabel } from "@/lib/dashboardWidgets";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { QueryError } from "@/components/ui/QueryError";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/utils/cn";

interface DashboardWidget {
  id: string;
  visible: boolean;
}

interface DashboardCustomizerProps {
  open: boolean;
  onClose: () => void;
}

export function DashboardCustomizer({ open, onClose }: DashboardCustomizerProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard-layout"],
    queryFn: () => api<{ widgets: DashboardWidget[] }>("/api/v1/dashboard/layout"),
    enabled: open,
  });

  const saveMutation = useMutation({
    mutationFn: (widgets: DashboardWidget[]) =>
      api<{ widgets: DashboardWidget[] }>("/api/v1/dashboard/layout", {
        method: "PUT",
        body: JSON.stringify({ widgets }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-layout"] });
      toast("success", "Dashboard layout saved");
      onClose();
    },
    onError: (e: Error) => toast("error", "Save failed", e.message),
  });

  const widgets = data?.widgets ?? [];

  function move(index: number, direction: -1 | 1) {
    const next = [...widgets];
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    saveMutation.mutate(next);
  }

  function toggle(index: number) {
    const next = widgets.map((w, i) => (i === index ? { ...w, visible: !w.visible } : w));
    saveMutation.mutate(next);
  }

  function remove(index: number) {
    const next = widgets.filter((_, i) => i !== index);
    if (!next.length) return;
    saveMutation.mutate(next);
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title="Customize dashboard"
      description="Show, hide, and reorder widgets"
      side="right"
    >
      {isLoading && <TableSkeleton rows={6} />}
      {isError && <QueryError onRetry={() => refetch()} />}
      {widgets.length > 0 && (
        <ul className="space-y-2">
          {widgets.map((w, index) => (
            <li
              key={w.id}
              className={cn(
                "flex items-center gap-2 p-3 rounded-lg border border-border-subtle",
                !w.visible && "opacity-60",
              )}
            >
              <LayoutGrid className="w-4 h-4 text-muted shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{widgetLabel(w.id)}</p>
                {w.id.startsWith("saved_search:") && (
                  <p className="text-xs text-muted font-mono truncate">{w.id}</p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button type="button" variant="ghost" size="sm" onClick={() => move(index, -1)} disabled={index === 0}>
                  ↑
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => move(index, 1)}
                  disabled={index === widgets.length - 1}
                >
                  ↓
                </Button>
                <Button type="button" variant="ghost" size="sm" onClick={() => toggle(index)}>
                  {w.visible ? "Hide" : "Show"}
                </Button>
                {w.id.startsWith("saved_search:") && (
                  <Button type="button" variant="ghost" size="sm" onClick={() => remove(index)} aria-label="Remove widget">
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted mt-4">
        Pin saved searches from the Search page to add more widgets here.
      </p>
    </Drawer>
  );
}
