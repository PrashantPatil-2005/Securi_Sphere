"use client";

import { PAGE_SIZES } from "@/lib/buildQuery";
import { cn } from "@/lib/utils/cn";

interface Props {
  page: number;
  pageSize: number;
  total: number;
  onPage: (p: number) => void;
  onPageSize: (s: number) => void;
}

export default function PaginationBar({ page, pageSize, total, onPage, onPageSize }: Props) {
  if (total === 0) return null;

  const pages = Math.max(1, Math.ceil(total / pageSize));
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mt-4 text-sm text-muted">
      <span className="tabular-nums">
        {start}–{end} of {total}
      </span>
      <div className="flex items-center gap-2">
        <select
          value={pageSize}
          onChange={(e) => onPageSize(+e.target.value)}
          className="input-siem py-1 px-2 text-sm"
          aria-label="Rows per page"
        >
          {PAGE_SIZES.map((s) => (
            <option key={s} value={s}>
              {s} rows
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className={cn("btn-ghost px-3 py-1 text-sm", page <= 1 && "opacity-40 pointer-events-none")}
        >
          Prev
        </button>
        <span className="text-caption normal-case tabular-nums">
          {page} / {pages}
        </span>
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          className={cn("btn-ghost px-3 py-1 text-sm", page >= pages && "opacity-40 pointer-events-none")}
        >
          Next
        </button>
      </div>
    </div>
  );
}
