"use client";

import Image from "next/image";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { PRODUCT_NAME } from "@/lib/brand";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <div className="min-h-screen flex">
        {/* Brand panel */}
        <div className="hidden lg:flex lg:w-[480px] xl:w-[540px] relative overflow-hidden bg-[#060a0f] shrink-0">
          <div className="absolute inset-0 bg-gradient-to-br from-accent/20 via-transparent to-transparent" />
          <div className="absolute inset-0 opacity-30" style={{
            backgroundImage: "radial-gradient(circle at 25% 25%, rgba(59,130,246,0.15) 0%, transparent 50%), radial-gradient(circle at 75% 75%, rgba(34,197,94,0.08) 0%, transparent 50%)",
          }} />
          <div className="relative z-10 flex flex-col justify-between p-10 xl:p-12">
            <div className="flex items-center gap-3">
              <Image
                src="/logo.webp"
                alt={PRODUCT_NAME}
                width={40}
                height={40}
                className="h-10 w-10 rounded-xl object-contain"
                priority
              />
              <div>
                <h1 className="text-heading font-semibold text-white">{PRODUCT_NAME}</h1>
                <p className="text-caption normal-case text-white/50">Enterprise Security Platform</p>
              </div>
            </div>
            <div>
              <blockquote className="text-xl font-medium text-white/90 leading-relaxed">
                Unified security operations for modern enterprises. Monitor, detect, and respond — in real time.
              </blockquote>
              <div className="mt-8 grid grid-cols-3 gap-4">
                {[
                  { value: "99.9%", label: "Uptime SLA" },
                  { value: "<2s", label: "Detection Latency" },
                  { value: "24/7", label: "Monitoring" },
                ].map((s) => (
                  <div key={s.label} className="p-3 rounded-lg bg-white/5 border border-white/10">
                    <p className="text-lg font-semibold text-white tabular-nums">{s.value}</p>
                    <p className="text-[11px] text-white/50 mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-caption normal-case text-white/30">
              © {new Date().getFullYear()} {PRODUCT_NAME}. All rights reserved.
            </p>
          </div>
        </div>

        {/* Form panel */}
        <div className="flex-1 flex items-center justify-center p-6 sm:p-10 bg-background">
          <div className="w-full max-w-md">
            <div className="lg:hidden flex items-center gap-3 mb-8">
              <Image
                src="/logo.webp"
                alt={PRODUCT_NAME}
                width={36}
                height={36}
                className="h-9 w-9 rounded-lg object-contain"
                priority
              />
              <span className="text-heading font-semibold">{PRODUCT_NAME}</span>
            </div>
            {children}
          </div>
        </div>
      </div>
    </ThemeProvider>
  );
}
