"use client";

import { memo, useRef, type ReactNode } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

interface Props<T> {
  items: T[];
  rowKey: (item: T, index: number) => string;
  renderItem: (item: T, index: number) => ReactNode;
  height?: number;
  estimateSize?: number;
  emptyMessage?: string;
}

function VirtualListInner<T>({
  items,
  rowKey,
  renderItem,
  height = 640,
  estimateSize = 96,
  emptyMessage = "No items.",
}: Props<T>) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan: 6,
  });

  if (items.length === 0) {
    return <p className="empty-desc py-8 text-center">{emptyMessage}</p>;
  }

  return (
    <div ref={parentRef} style={{ height, overflow: "auto", contain: "strict" }}>
      <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
        {virtualizer.getVirtualItems().map((vRow) => {
          const item = items[vRow.index];
          return (
            <div
              key={rowKey(item, vRow.index)}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${vRow.start}px)`,
              }}
            >
              {renderItem(item, vRow.index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export const VirtualList = memo(VirtualListInner) as typeof VirtualListInner;
