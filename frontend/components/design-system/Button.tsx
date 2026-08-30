"use client";

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "outline" | "link";
type Size = "xs" | "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-primary bg-card-elevated text-foreground border border-border hover:bg-card",
  ghost: "btn-ghost",
  danger: "btn-danger",
  outline: "btn-outline",
  link: "text-accent hover:underline bg-transparent border-none p-0",
};

const sizes: Record<Size, string> = {
  xs: "px-2 py-1 text-[11px] rounded",
  sm: "px-2.5 py-1.5 text-caption",
  md: "px-4 py-2 text-body",
  lg: "px-5 py-2.5 text-body",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      className,
      variant = "primary",
      size = "md",
      loading,
      disabled,
      icon,
      iconRight,
      children,
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        className={cn(
          variants[variant],
          variant !== "link" && sizes[size],
          className,
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <span className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {!loading && icon && <span className="shrink-0 [&>svg]:w-4 [&>svg]:h-4">{icon}</span>}
        {children}
        {iconRight && <span className="shrink-0 [&>svg]:w-4 [&>svg]:h-4">{iconRight}</span>}
      </button>
    );
  },
);
