"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen ambient-bg">
      <Sidebar className="hidden lg:flex" />
      {mobileOpen && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <Sidebar
            drawer
            className="fixed inset-y-0 left-0 z-50 lg:hidden shadow-2xl"
            onClose={() => setMobileOpen(false)}
          />
        </>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav showMenu onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 p-4 lg:p-6 overflow-auto space-y-8">
          {children}
        </main>
      </div>
    </div>
  );
}
