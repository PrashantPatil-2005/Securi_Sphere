"use client";

import { useState } from "react";
import Link from "next/link";
import { Shield } from "lucide-react";
import { PRODUCT_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils/cn";

interface BrandLogoProps {
  collapsed?: boolean;
  className?: string;
  asLink?: boolean;
}

export function BrandLogo({ collapsed = false, className, asLink = true }: BrandLogoProps) {
  const [imgFailed, setImgFailed] = useState(false);
  const size = collapsed ? 32 : 40;

  const logoEl = imgFailed ? (
    <div
      className={cn(
        "shrink-0 rounded-lg bg-accent/15 flex items-center justify-center",
        collapsed ? "h-8 w-8" : "h-10 w-10",
      )}
    >
      <Shield className={cn("text-accent", collapsed ? "w-5 h-5" : "w-6 h-6")} />
    </div>
  ) : (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/logo.webp"
      alt={PRODUCT_NAME}
      width={size}
      height={size}
      className={cn(
        "shrink-0 object-contain",
        collapsed ? "h-8 w-8" : "h-10 w-10",
      )}
      onError={() => setImgFailed(true)}
    />
  );

  const content = (
    <div className={cn("flex items-center gap-3 min-w-0", collapsed && "justify-center", className)}>
      {logoEl}
      {!collapsed && (
        <div className="min-w-0">
          <p className="text-sm font-semibold tracking-tight text-foreground truncate leading-tight">
            {PRODUCT_NAME}
          </p>
          <p className="text-[10px] text-muted uppercase tracking-widest leading-tight mt-0.5">
            Enterprise Security Platform
          </p>
        </div>
      )}
    </div>
  );

  if (asLink) {
    return (
      <Link href="/" className="block hover:opacity-90 transition-opacity" aria-label={`${PRODUCT_NAME} home`}>
        {content}
      </Link>
    );
  }

  return content;
}
