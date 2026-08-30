import { cn } from "@/lib/utils/cn";

interface LoadingStateProps {
  variant?: "page" | "table" | "card" | "chart" | "inline";
  rows?: number;
  className?: string;
  text?: string;
}

export function LoadingState({
  variant = "inline",
  rows = 8,
  className,
  text,
}: LoadingStateProps) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3", className)}
      role="status"
      aria-busy
      aria-label={text || "Loading"}
    >
      {variant === "page" && <PageSkeleton />}
      {variant === "table" && <TableSkeleton rows={rows} />}
      {variant === "card" && <CardSkeletonGroup />}
      {variant === "chart" && <ChartSkeleton />}
      {variant === "inline" && (
        <div className="flex items-center gap-2 text-muted">
          <span className="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
          {text && <span className="text-sm">{text}</span>}
        </div>
      )}
      {!text && variant !== "inline" && (
        <span className="text-sm text-muted">Loading\u2026</span>
      )}
    </div>
  );
}

export function Skeleton({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`skeleton rounded-md ${className}`} style={style} aria-hidden />;
}

export function PageSkeleton() {
  return (
    <div className="space-y-4" aria-busy aria-label="Loading page">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-64" />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="panel p-4 space-y-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-7 w-16" />
          </div>
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="data-table-wrap" aria-busy aria-label="Loading table">
      <div className="bg-card-elevated px-3 py-2.5 border-b border-border-subtle">
        <Skeleton className="h-3 w-full" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex items-center border-b border-border-subtle px-3 py-2.5"
        >
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-20 ml-4" />
          <Skeleton className="h-4 w-16 ml-4" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeletonGroup() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4" aria-busy aria-label="Loading cards">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="panel p-4 space-y-3">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-3 w-32" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ height = 260 }: { height?: number }) {
  return (
    <div aria-busy aria-label="Loading chart">
      <Skeleton className="w-full rounded-md" style={{ height }} />
    </div>
  );
}
