"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

type Variant = "primary" | "ghost" | "danger" | "link";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary: "btn-primary",
  ghost: "btn-ghost",
  danger: "btn-danger",
  link: "text-accent hover:underline bg-transparent border-none p-0",
};

const sizes: Record<Size, string> = {
  sm: "px-2.5 py-1.5 text-caption",
  md: "px-4 py-2 text-body",
  lg: "px-5 py-2.5 text-body",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ className, variant = "primary", size = "md", loading, disabled, children, ...props }, ref) {
    return (
      <button
        ref={ref}
        className={cn(variants[variant], variant !== "link" && sizes[size], className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {children}
      </button>
    );
  },
);
