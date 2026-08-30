import { type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

export interface Column<T> {
  key: string;
  header: string;
  className?: string;
  render?: (item: T, index: number) => ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: (item: T, index: number) => string | number;
  onRowClick?: (item: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  className?: string;
  compact?: boolean;
}

export function DataTable<T>({
  columns,
  data,
  rowKey,
  onRowClick,
  emptyTitle = "No data",
  emptyDescription,
  className,
  compact,
}: DataTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="empty-state py-10">
        <p className="empty-title">{emptyTitle}</p>
        {emptyDescription && <p className="empty-desc">{emptyDescription}</p>}
      </div>
    );
  }

  return (
    <div className={cn("data-table-wrap", className)}>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={col.className}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, i) => (
              <tr
                key={rowKey(item, i)}
                className={cn(
                  "data-table-row",
                  onRowClick && "cursor-pointer",
                  compact && "!py-1.5",
                )}
                onClick={onRowClick ? () => onRowClick(item) : undefined}
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn("data-table-cell", col.className)}>
                    {col.render
                      ? col.render(item, i)
                      : String((item as Record<string, unknown>)[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
