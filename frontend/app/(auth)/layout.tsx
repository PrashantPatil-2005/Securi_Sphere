"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import { ThemeProvider } from "@/lib/theme/ThemeProvider";
import { PRODUCT_NAME } from "@/lib/brand";

function AuthLogo({ size = 40, className }: { size?: number; className?: string }) {
  const [imgFailed, setImgFailed] = useState(false);
  if (imgFailed) {
    return (
      <div className={`rounded-xl bg-white/10 flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
        <Shield className="text-white/80" style={{ width: size * 0.6, height: size * 0.6 }} />
      </div>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/logo.webp"
      alt={PRODUCT_NAME}
      width={size}
      height={size}
      className={`rounded-xl object-contain ${className}`}
      onError={() => setImgFailed(true)}
    />
  );
}

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
              <AuthLogo size={40} className="h-10 w-10" />
              <div>
                <h1 className="text-heading font-semibold text-white">{PRODUCT_NAME}</h1>
                <p className="text-caption normal-case text-white/50">Enterprise Security Platform</p>
              </div>
            </div>
            <div>
              <blockquote className="text-xl font-medium text-white/90 leading-relaxed">
                Unified security operations for modern enterprises. Monitor, detect, and respond — in real time.
              </blockquote>
              <div className="mt-10 grid grid-cols-3 gap-3">
                {[
                  { value: "99.9%", label: "Uptime SLA" },
                  { value: "<2s", label: "Detection Latency" },
                  { value: "24/7", label: "Monitoring" },
                ].map((s) => (
                  <div
                    key={s.label}
                    className="flex flex-col items-center rounded-xl bg-white/5 border border-white/10 min-h-[112px] pt-5 pb-4"
                  >
                    <p className="text-2xl font-semibold text-white tabular-nums leading-none">{s.value}</p>
                    <p className="mt-3 px-1 text-center text-[10px] font-medium uppercase tracking-[0.08em] text-white/50 leading-snug">
                      {s.label}
                    </p>
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
              <AuthLogo size={36} className="h-9 w-9" />
              <span className="text-heading font-semibold">{PRODUCT_NAME}</span>
            </div>
            {children}
          </div>
        </div>
      </div>
    </ThemeProvider>
  );
}
