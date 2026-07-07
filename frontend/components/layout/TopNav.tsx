"use client";

import { memo, useCallback, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Bell, Moon, Sun, User, Settings, LogOut, Menu } from "lucide-react";
import { logoutApi } from "@/lib/api";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { useDropdown } from "@/lib/hooks/useDropdown";
import {
  useNotificationHistory,
  useNotificationMutations,
  useUnreadNotificationCount,
  notificationHref,
} from "@/lib/hooks/useNotifications";
import { useWsMessages } from "@/lib/websocket";
import { cn } from "@/lib/utils/cn";
import { ConnectionBanner } from "./ConnectionBanner";
import { DemoModeBanner } from "./DemoModeBanner";

function NotificationCenter() {
  const queryClient = useQueryClient();
  const { open, toggle, close, containerRef, triggerRef, panelRef, panelId } = useDropdown();
  const { data: unreadData } = useUnreadNotificationCount();
  const { data: history } = useNotificationHistory(1, 10);
  const { markRead, markAllRead } = useNotificationMutations();

  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  }, [queryClient]);

  useWsMessages(["new_alert"], refresh);

  const notifications = history?.items ?? [];
  const unread = unreadData?.unread_count ?? 0;

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        className="relative p-2 rounded-md text-muted hover:text-foreground hover:bg-[var(--sidebar-hover)] transition-colors"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
        aria-expanded={open}
        aria-haspopup="true"
        aria-controls={panelId}
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 text-[10px] font-bold bg-danger text-white rounded-full flex items-center justify-center" aria-hidden>
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            ref={panelRef}
            id={panelId}
            role="menu"
            aria-label="Notifications"
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-80 bg-card border border-border-subtle rounded-lg shadow-lg z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
              <span className="text-body font-semibold">Notifications</span>
              {unread > 0 && (
                <button
                  type="button"
                  onClick={() => markAllRead.mutate()}
                  disabled={markAllRead.isPending}
                  className="text-caption normal-case text-accent hover:underline"
                >
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="px-4 py-8 text-body text-muted text-center">No notifications</p>
              ) : (
                notifications.map((n) => {
                  const href = notificationHref(n);
                  const row = (
                    <div
                      className={cn(
                        "px-4 py-3 border-b border-border-subtle/50 hover:bg-[var(--sidebar-hover)] transition-colors",
                        !n.read && "bg-accent/5",
                      )}
                    >
                      <p className="text-body font-medium">{n.title}</p>
                      <p className="text-caption normal-case text-muted mt-0.5">
                        {new Date(n.created_at).toLocaleString()}
                      </p>
                    </div>
                  );

                  if (href) {
                    return (
                      <Link
                        key={n.id}
                        href={href}
                        role="menuitem"
                        onClick={() => {
                          if (!n.read) markRead.mutate(n.id);
                          close();
                        }}
                      >
                        {row}
                      </Link>
                    );
                  }
                  return (
                    <button
                      key={n.id}
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        if (!n.read) markRead.mutate(n.id);
                      }}
                      className="w-full text-left"
                    >
                      {row}
                    </button>
                  );
                })
              )}
            </div>
            <div className="px-4 py-2 border-t border-border-subtle text-center">
              <Link href="/notifications" onClick={close} className="text-caption normal-case text-accent hover:underline">
                View all history
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const UserMenu = memo(function UserMenu() {
  const { open, toggle, close, containerRef, triggerRef, panelRef, panelId } = useDropdown();
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  const logout = useCallback(async () => {
    close();
    await logoutApi();
    router.push("/login");
  }, [close, router]);

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={toggle}
        className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent hover:bg-accent/30 transition-colors"
        aria-label="User menu"
        aria-expanded={open}
        aria-haspopup="true"
        aria-controls={panelId}
      >
        <User className="w-4 h-4" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            ref={panelRef}
            id={panelId}
            role="menu"
            aria-label="User menu"
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-48 bg-card border border-border-subtle rounded-lg shadow-lg z-50 py-1"
          >
            <Link
              href="/profile"
              role="menuitem"
              onClick={close}
              className="flex items-center gap-2 px-4 py-2 text-body hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <User className="w-4 h-4 text-muted" /> Profile
            </Link>
            <Link
              href="/settings"
              role="menuitem"
              onClick={close}
              className="flex items-center gap-2 px-4 py-2 text-body hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <Settings className="w-4 h-4 text-muted" /> Settings
            </Link>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                toggleTheme();
                close();
              }}
              className="flex items-center gap-2 px-4 py-2 text-body hover:bg-[var(--sidebar-hover)] transition-colors w-full text-left"
            >
              {theme === "dark" ? <Sun className="w-4 h-4 text-muted" /> : <Moon className="w-4 h-4 text-muted" />}
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </button>
            <div className="border-t border-border-subtle my-1" role="separator" />
            <button
              type="button"
              role="menuitem"
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 text-body text-danger hover:bg-danger/10 transition-colors w-full text-left"
            >
              <LogOut className="w-4 h-4" /> Sign out
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

interface TopNavProps {
  onMenuClick?: () => void;
  showMenu?: boolean;
}

export function TopNav({ onMenuClick, showMenu }: TopNavProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <header className="sticky top-0 z-40 glass-nav border-b shrink-0">
      <div className="flex items-center gap-4 px-4 lg:px-6 h-14">
        {showMenu && (
          <button type="button" onClick={onMenuClick} className="p-2 rounded-md text-muted hover:text-foreground lg:hidden" aria-label="Open menu">
            <Menu className="w-5 h-5" />
          </button>
        )}

        <form onSubmit={handleSearch} className="flex-1 max-w-xl">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" aria-hidden />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search events, alerts, hosts…"
              className="w-full pl-9 pr-4 py-1.5 text-body bg-[var(--input-bg)] border border-border-subtle rounded-md text-foreground placeholder:text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
              aria-label="Global search"
            />
          </div>
        </form>

        <div className="flex items-center gap-1 ml-auto">
          <NotificationCenter />
          <UserMenu />
        </div>
      </div>
      <ConnectionBanner />
      <DemoModeBanner />
    </header>
  );
}
