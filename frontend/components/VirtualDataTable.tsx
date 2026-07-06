"use client";

import { memo, useMemo, useRef, type ReactNode } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { EmptyState } from "@/components/ui/Panel";

export interface Column<T> {
  key: string;
  header: string;
  width?: string;
  render: (row: T) => ReactNode;
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  height?: number;
  rowHeight?: number;
  emptyMessage?: string;
  emptyTitle?: string;
  emptyIcon?: ReactNode;
  emptyAction?: string;
  emptyActionLabel?: string;
  renderMobileCard?: (row: T) => ReactNode;
}

function VirtualDataTableInner<T>({
  rows,
  columns,
  rowKey,
  height = 520,
  rowHeight = 44,
  emptyMessage = "No records match your filters.",
  emptyTitle,
  emptyIcon,
  emptyAction,
  emptyActionLabel,
  renderMobileCard,
}: Props<T>) {
  const isMobile = useMediaQuery("(max-width: 767px)");
  const parentRef = useRef<HTMLDivElement>(null);
  const gridCols = useMemo(() => columns.map((c) => c.width || "1fr").join(" "), [columns]);
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 8,
  });

  if (rows.length === 0) {
    if (emptyTitle || emptyIcon) {
      return (
        <EmptyState
          title={emptyTitle ?? "No results"}
          description={emptyMessage}
          icon={emptyIcon}
          action={emptyAction}
          actionLabel={emptyActionLabel}
        />
      );
    }
    return <p className="empty-desc py-8 text-center">{emptyMessage}</p>;
  }

  if (isMobile && renderMobileCard) {
    return (
      <div className="space-y-2 md:hidden">
        {rows.map((row) => (
          <div key={rowKey(row)} className="panel p-3">
            {renderMobileCard(row)}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} style={{ width: c.width }}>{c.header}</th>
            ))}
          </tr>
        </thead>
      </table>
      <div ref={parentRef} className="data-table-body" style={{ height, overflow: "auto", contain: "strict" }}>
        <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
          {virtualizer.getVirtualItems().map((vRow) => {
            const row = rows[vRow.index];
            return (
              <div
                key={rowKey(row)}
                className="data-table-row"
                style={{
                  display: "grid",
                  gridTemplateColumns: gridCols,
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: vRow.size,
                  transform: `translateY(${vRow.start}px)`,
                }}
              >
                {columns.map((c) => (
                  <div key={c.key} className="data-table-cell">
                    {c.render(row)}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export const VirtualDataTable = memo(VirtualDataTableInner) as typeof VirtualDataTableInner;
