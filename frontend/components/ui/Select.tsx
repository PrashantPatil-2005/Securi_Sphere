"use client";

import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  function Select({ className, label, hint, id, children, ...props }, ref) {
    const selectId = id || label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={selectId} className="block text-body font-medium text-foreground">
            {label}
          </label>
        )}
        <select ref={ref} id={selectId} className={cn("input-siem", className)} {...props}>
          {children}
        </select>
        {hint && (
          <p className="text-caption normal-case text-muted">{hint}</p>
        )}
      </div>
    );
  },
);
