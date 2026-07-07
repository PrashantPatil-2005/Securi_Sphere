import Image from "next/image";
import Link from "next/link";
import { PRODUCT_NAME, PRODUCT_TAGLINE } from "@/lib/brand";
import { cn } from "@/lib/utils/cn";

interface BrandLogoProps {
  collapsed?: boolean;
  className?: string;
  asLink?: boolean;
}

export function BrandLogo({ collapsed = false, className, asLink = true }: BrandLogoProps) {
  const content = (
    <div className={cn("flex items-center gap-3 min-w-0", collapsed && "justify-center", className)}>
      <Image
        src="/logo.webp"
        alt={PRODUCT_NAME}
        width={collapsed ? 32 : 40}
        height={collapsed ? 32 : 40}
        className={cn(
          "shrink-0 object-contain",
          collapsed ? "h-8 w-8" : "h-10 w-10",
        )}
        priority
      />
      {!collapsed && (
        <div className="min-w-0">
          <p className="text-sm font-semibold tracking-tight text-foreground truncate leading-tight">
            {PRODUCT_NAME}
          </p>
          <p className="text-[10px] text-muted uppercase tracking-widest leading-tight mt-0.5">
            {PRODUCT_TAGLINE}
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
