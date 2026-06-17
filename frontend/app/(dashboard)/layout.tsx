"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearTokens } from "@/lib/api";
import { TimeRangeProvider } from "@/lib/timeRange";
import { useWebSocket } from "@/lib/websocket";

const nav = [
  { href: "/", label: "Overview" },
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

function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [toast, setToast] = useState<string | null>(null);
  const { connected } = useWebSocket((msg) => {
    if (msg.type === "new_alert") {
      setToast(`New alert: ${msg.data.title}`);
      setTimeout(() => setToast(null), 5000);
    }
  });

  useEffect(() => {
    if (!localStorage.getItem("access_token")) router.push("/login");
  }, [router]);

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-[var(--card)] border-r border-[var(--border)] p-4 flex flex-col shrink-0">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-blue-400">SecuriSphere</h1>
          <p className="text-xs text-gray-500">Mini SIEM</p>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto">
          {nav.map((item) => (
            <Link key={item.href} href={item.href}
              className={`block px-3 py-1.5 rounded text-sm ${pathname === item.href ? "bg-blue-600/20 text-blue-400" : "text-gray-400 hover:text-white hover:bg-white/5"}`}>
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="text-xs text-gray-500 mb-2 mt-4">
          WS: {connected ? <span className="text-green-400">Connected</span> : <span className="text-red-400">Disconnected</span>}
        </div>
        <button onClick={() => { clearTokens(); router.push("/login"); }} className="text-sm text-gray-400 hover:text-white text-left px-3 py-2">Logout</button>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
      {toast && <div className="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-3 rounded shadow-lg z-50">{toast}</div>}
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <TimeRangeProvider>
      <DashboardShell>{children}</DashboardShell>
    </TimeRangeProvider>
  );
}
