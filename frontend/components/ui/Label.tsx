"use client";

import { forwardRef, type LabelHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export const Label = forwardRef<HTMLLabelElement, LabelProps>(function Label(
  { className, children, required, ...props },
  ref,
) {
  return (
    <label
      ref={ref}
      className={cn("block text-body font-medium text-foreground", className)}
      {...props}
    >
      {children}
      {required && <span className="text-danger ml-0.5" aria-hidden>*</span>}
    </label>
  );
});
