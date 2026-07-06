"use client";

import { useState } from "react";
import Link from "next/link";
import { Bell } from "lucide-react";
import {
  useNotificationHistory,
  useNotificationMutations,
  notificationHref,
} from "@/lib/hooks/useNotifications";
import PaginationBar from "@/components/PaginationBar";
import { PageHeader, EmptyState } from "@/components/ui/Panel";
import { FilterBar } from "@/components/ui/FilterBar";
import { QueryError } from "@/components/ui/QueryError";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils/cn";

export default function NotificationsPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { data, isLoading, isError, refetch, isFetching } = useNotificationHistory(page, pageSize, unreadOnly);
  const { markRead, markAllRead } = useNotificationMutations();

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle="In-app history for alerts and offenses"
        action={
          (data?.unread_count ?? 0) > 0 ? (
            <button
              type="button"
              disabled={markAllRead.isPending}
              onClick={() => markAllRead.mutate()}
              className="btn-ghost text-sm"
            >
              Mark all read
            </button>
          ) : undefined
        }
      />

      <FilterBar>
        <label className="flex items-center gap-2 text-sm text-[var(--muted)] cursor-pointer">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(e) => {
              setUnreadOnly(e.target.checked);
              setPage(1);
            }}
          />
          Unread only
        </label>
        {data && (
          <span className="text-sm text-[var(--muted)] ml-auto">
            {data.unread_count} unread · {data.total} total
          </span>
        )}
      </FilterBar>

      {isLoading ? (
        <TableSkeleton rows={8} />
      ) : isError ? (
        <QueryError onRetry={() => refetch()} />
      ) : (
        <div className={isFetching ? "opacity-70 transition-opacity" : ""}>
          {(data?.items ?? []).length === 0 ? (
            <EmptyState
              title="No notifications"
              description={unreadOnly ? "You're all caught up." : "New alerts and offenses will appear here."}
              icon={<Bell className="w-10 h-10 opacity-40" />}
            />
          ) : (
            <div className="space-y-2">
              {data?.items.map((item) => {
                const href = notificationHref(item);
                const content = (
                  <div
                    className={cn(
                      "panel p-4 flex items-start gap-3 transition-colors",
                      !item.read && "border-accent/30 bg-accent/5",
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        {item.severity && <SeverityBadge severity={item.severity} />}
                        <span className="text-xs uppercase tracking-wide text-[var(--muted)]">{item.kind}</span>
                        {!item.read && (
                          <span className="text-[10px] font-semibold text-accent uppercase">New</span>
                        )}
                      </div>
                      <p className="font-medium text-sm">{item.title}</p>
                      {item.body && <p className="text-sm text-[var(--muted)] mt-1">{item.body}</p>}
                      <p className="text-[11px] text-[var(--muted)] mt-2 tabular-nums">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>
                    {!item.read && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          markRead.mutate(item.id);
                        }}
                        className="btn-ghost text-xs shrink-0"
                      >
                        Mark read
                      </button>
                    )}
                  </div>
                );

                return href ? (
                  <Link
                    key={item.id}
                    href={href}
                    onClick={() => {
                      if (!item.read) markRead.mutate(item.id);
                    }}
                    className="block hover:opacity-90"
                  >
                    {content}
                  </Link>
                ) : (
                  <div key={item.id}>{content}</div>
                );
              })}
            </div>
          )}
          <PaginationBar
            page={page}
            pageSize={pageSize}
            total={data?.total ?? 0}
            onPage={setPage}
            onPageSize={(s) => {
              setPageSize(s);
              setPage(1);
            }}
          />
        </div>
      )}
    </div>
  );
}
