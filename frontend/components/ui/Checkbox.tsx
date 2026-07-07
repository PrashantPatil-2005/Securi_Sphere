"use client";

import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";
import { Label } from "./Label";

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  hint?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className, label, hint, id, ...props },
  ref,
) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

  if (!label) {
    return (
      <input
        ref={ref}
        type="checkbox"
        id={inputId}
        className={cn(
          "h-4 w-4 rounded border-border-subtle bg-[var(--input-bg)] text-accent focus:ring-accent/30",
          className,
        )}
        {...props}
      />
    );
  }

  return (
    <div className="flex items-start gap-2">
      <input
        ref={ref}
        type="checkbox"
        id={inputId}
        className={cn(
          "mt-0.5 h-4 w-4 shrink-0 rounded border-border-subtle bg-[var(--input-bg)] text-accent focus:ring-accent/30",
          className,
        )}
        {...props}
      />
      <div className="space-y-0.5">
        <Label htmlFor={inputId} className="font-normal cursor-pointer">
          {label}
        </Label>
        {hint && <p className="text-caption normal-case text-muted">{hint}</p>}
      </div>
    </div>
  );
});
