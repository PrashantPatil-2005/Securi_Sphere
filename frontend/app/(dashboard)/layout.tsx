"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearTokens } from "@/lib/api";
import { useWebSocket } from "@/lib/websocket";

const nav = [
  { href: "/", label: "Overview" },
  { href: "/hosts", label: "Hosts" },
  { href: "/events", label: "Events" },
  { href: "/alerts", label: "Alerts" },
  { href: "/metrics", label: "Metrics" },
  { href: "/search", label: "Search" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
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
    if (!localStorage.getItem("access_token")) {
      router.push("/login");
    }
  }, [router]);

  function logout() {
    clearTokens();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-[var(--card)] border-r border-[var(--border)] p-4 flex flex-col">
        <div className="mb-8">
          <h1 className="text-xl font-bold text-blue-400">Securi</h1>
          <p className="text-xs text-gray-500">Mini SIEM</p>
        </div>
        <nav className="flex-1 space-y-1">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded text-sm ${
                pathname === item.href ? "bg-blue-600/20 text-blue-400" : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="text-xs text-gray-500 mb-2">
          WS: {connected ? <span className="text-green-400">Connected</span> : <span className="text-red-400">Disconnected</span>}
        </div>
        <button onClick={logout} className="text-sm text-gray-400 hover:text-white text-left px-3 py-2">
          Logout
        </button>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
      {toast && (
        <div className="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-3 rounded shadow-lg z-50">
          {toast}
        </div>
      )}
    </div>
  );
}
