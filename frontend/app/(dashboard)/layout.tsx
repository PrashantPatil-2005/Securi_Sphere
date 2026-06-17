"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { memo, useCallback, useEffect, useState } from "react";
import { clearTokens } from "@/lib/api";
import { AppProviders } from "@/lib/providers";
import { TimeRangeProvider } from "@/lib/timeRange";
import { useWsConnected, useWsMessages } from "@/lib/websocket";

const nav = [
  { href: "/", label: "Executive" },
  { href: "/analytics", label: "Analytics" },
  { href: "/offenses", label: "Offenses" },
  { href: "/hosts", label: "Hosts" },
  { href: "/events", label: "Events" },
  { href: "/alerts", label: "Alerts" },
  { href: "/metrics", label: "Metrics" },
  { href: "/mitre", label: "MITRE" },
  { href: "/timeline", label: "Timeline" },
  { href: "/incidents", label: "Incidents" },
  { href: "/network", label: "Network" },
  { href: "/rules", label: "Rules" },
  { href: "/audit", label: "Audit" },
  { href: "/simulation", label: "Simulation" },
  { href: "/reports", label: "Reports" },
  { href: "/search", label: "Search" },
];

const NavLink = memo(function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link href={href} className={`nav-link ${active ? "nav-link-active" : "nav-link-idle"}`}>
      {label}
    </Link>
  );
});

function AlertToast() {
  const [toast, setToast] = useState<string | null>(null);
  useWsMessages(["new_alert"], (msg) => {
    const title = String(msg.data.title || "New alert");
    setToast(title);
    setTimeout(() => setToast(null), 5000);
  });
  if (!toast) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 animate-fade-in px-4 py-3 rounded-md border border-red-900/50 bg-red-950/90 text-red-100 text-sm shadow-lg">
      Alert: {toast}
    </div>
  );
}

function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const connected = useWsConnected();

  useEffect(() => {
    if (!localStorage.getItem("access_token")) router.push("/login");
  }, [router]);

  const logout = useCallback(() => {
    clearTokens();
    router.push("/login");
  }, [router]);

  return (
    <aside className="w-56 bg-[var(--card)] border-r border-[var(--border-subtle)] flex flex-col shrink-0">
      <div className="px-4 py-4 border-b border-[var(--border-subtle)]">
        <h1 className="text-base font-semibold tracking-tight text-[var(--accent)]">SecuriSphere</h1>
        <p className="text-[11px] text-[var(--muted)] uppercase tracking-widest mt-0.5">Security Operations</p>
      </div>
      <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
        {nav.map((item) => (
          <NavLink key={item.href} href={item.href} label={item.label} active={pathname === item.href} />
        ))}
      </nav>
      <div className="p-3 border-t border-[var(--border-subtle)] text-[11px] text-[var(--muted)]">
        <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${connected ? "bg-[var(--success)]" : "bg-[var(--danger)]"}`} />
        {connected ? "Live feed connected" : "Reconnecting…"}
        <button onClick={logout} className="block mt-2 text-left hover:text-[var(--foreground)] transition-colors">
          Sign out
        </button>
      </div>
    </aside>
  );
}

function DashboardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-5 overflow-auto animate-fade-in">{children}</main>
      <AlertToast />
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppProviders>
      <TimeRangeProvider>
        <DashboardShell>{children}</DashboardShell>
      </TimeRangeProvider>
    </AppProviders>
  );
}
