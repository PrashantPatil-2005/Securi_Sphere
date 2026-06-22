import { TableSkeleton } from "./Skeleton";

export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-48 rounded bg-[var(--sidebar-hover)]" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-[var(--sidebar-hover)]" />
        ))}
      </div>
      <TableSkeleton rows={8} />
    </div>
  );
}
