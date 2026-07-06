"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { PageTransition } from "./PageTransition";
import { AIAssistantPanel } from "@/components/AIAssistantPanel";
import { CommandPalette } from "@/components/CommandPalette";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen ambient-bg">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-md focus:bg-card focus:border focus:border-border focus:text-foreground focus:shadow-lg"
      >
        Skip to main content
      </a>
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
        <main id="main-content" tabIndex={-1} className="flex-1 p-4 lg:p-6 overflow-auto space-y-8 outline-none">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
      <CommandPalette />
      <AIAssistantPanel />
    </div>
  );
}
