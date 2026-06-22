"use client";

import { memo, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Bell, Moon, Sun, User, Settings, LogOut, Menu } from "lucide-react";
import { logoutApi } from "@/lib/api";
import { useTheme } from "@/lib/theme/ThemeProvider";
import { useWsMessages } from "@/lib/websocket";
import { cn } from "@/lib/utils/cn";

interface Notification {
  id: string;
  title: string;
  time: string;
  read: boolean;
}

function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  useWsMessages(["new_alert"], (msg) => {
    const title = String(msg.data.title || "New security alert");
    setNotifications((prev) => [
      { id: crypto.randomUUID(), title, time: new Date().toLocaleTimeString(), read: false },
      ...prev.slice(0, 19),
    ]);
  });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const unread = notifications.filter((n) => !n.read).length;

  const markAllRead = () => setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-2 rounded-md text-muted hover:text-foreground hover:bg-[var(--sidebar-hover)] transition-colors"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 text-[10px] font-bold bg-danger text-white rounded-full flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-80 bg-card border border-border-subtle rounded-lg shadow-lg z-50 overflow-hidden"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
              <span className="text-body font-semibold">Notifications</span>
              {unread > 0 && (
                <button onClick={markAllRead} className="text-caption normal-case text-accent hover:underline">
                  Mark all read
                </button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="px-4 py-8 text-body text-muted text-center">No notifications</p>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    className={cn(
                      "px-4 py-3 border-b border-border-subtle/50 hover:bg-[var(--sidebar-hover)] transition-colors",
                      !n.read && "bg-accent/5",
                    )}
                  >
                    <p className="text-body font-medium">{n.title}</p>
                    <p className="text-caption normal-case text-muted mt-0.5">{n.time}</p>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const UserMenu = memo(function UserMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const logout = useCallback(async () => {
    await logoutApi();
    router.push("/login");
  }, [router]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center text-accent hover:bg-accent/30 transition-colors"
        aria-label="User menu"
      >
        <User className="w-4 h-4" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-48 bg-card border border-border-subtle rounded-lg shadow-lg z-50 py-1"
          >
            <Link href="/profile" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2 text-body hover:bg-[var(--sidebar-hover)] transition-colors">
              <User className="w-4 h-4 text-muted" /> Profile
            </Link>
            <Link href="/settings" onClick={() => setOpen(false)} className="flex items-center gap-2 px-4 py-2 text-body hover:bg-[var(--sidebar-hover)] transition-colors">
              <Settings className="w-4 h-4 text-muted" /> Settings
            </Link>
            <button onClick={toggleTheme} className="flex items-center gap-2 px-4 py-2 text-body hover:bg-[var(--sidebar-hover)] transition-colors w-full text-left">
              {theme === "dark" ? <Sun className="w-4 h-4 text-muted" /> : <Moon className="w-4 h-4 text-muted" />}
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </button>
            <div className="border-t border-border-subtle my-1" />
            <button onClick={logout} className="flex items-center gap-2 px-4 py-2 text-body text-danger hover:bg-danger/10 transition-colors w-full text-left">
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
    <header className="sticky top-0 z-40 flex items-center gap-4 px-4 lg:px-6 h-14 glass-nav border-b shrink-0">
      {showMenu && (
        <button onClick={onMenuClick} className="p-2 rounded-md text-muted hover:text-foreground lg:hidden" aria-label="Open menu">
          <Menu className="w-5 h-5" />
        </button>
      )}

      <form onSubmit={handleSearch} className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
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
    </header>
  );
}
