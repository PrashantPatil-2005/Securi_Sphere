"use client";

import { PAGE_SIZES } from "@/lib/buildQuery";

interface Props {
  page: number;
  pageSize: number;
  total: number;
  onPage: (p: number) => void;
  onPageSize: (s: number) => void;
}

export default function PaginationBar({ page, pageSize, total, onPage, onPageSize }: Props) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mt-4 text-sm text-gray-400">
      <span>{total} total · page {page} of {pages}</span>
      <div className="flex items-center gap-2">
        <select value={pageSize} onChange={(e) => onPageSize(+e.target.value)}
          className="px-2 py-1 bg-black/30 border border-[var(--border)] rounded">
          {PAGE_SIZES.map((s) => <option key={s} value={s}>{s} rows</option>)}
        </select>
        <button disabled={page <= 1} onClick={() => onPage(page - 1)} className="px-3 py-1 rounded border border-[var(--border)] disabled:opacity-40">Prev</button>
        <button disabled={page >= pages} onClick={() => onPage(page + 1)} className="px-3 py-1 rounded border border-[var(--border)] disabled:opacity-40">Next</button>
      </div>
    </div>
  );
}
