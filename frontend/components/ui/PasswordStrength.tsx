"use client";

import { memo, useMemo } from "react";
import { cn } from "@/lib/utils/cn";

interface PasswordStrengthProps {
  password: string;
}

const checks = [
  { test: (p: string) => p.length >= 8, label: "8+ characters" },
  { test: (p: string) => /[A-Z]/.test(p), label: "Uppercase" },
  { test: (p: string) => /[a-z]/.test(p), label: "Lowercase" },
  { test: (p: string) => /[0-9]/.test(p), label: "Number" },
  { test: (p: string) => /[^A-Za-z0-9]/.test(p), label: "Special char" },
];

export const PasswordStrength = memo(function PasswordStrength({ password }: PasswordStrengthProps) {
  const score = useMemo(() => checks.filter((c) => c.test(password)).length, [password]);
  const strength = score <= 2 ? "weak" : score <= 4 ? "medium" : "strong";
  const colors = { weak: "bg-danger", medium: "bg-warning", strong: "bg-success" };

  if (!password) return null;

  return (
    <div className="space-y-2" aria-live="polite">
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className={cn("h-1 flex-1 rounded-full transition-colors duration-fast", i <= score ? colors[strength] : "bg-border")}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {checks.map((c) => (
          <span
            key={c.label}
            className={cn("text-[11px]", c.test(password) ? "text-success" : "text-muted")}
          >
            {c.test(password) ? "✓" : "○"} {c.label}
          </span>
        ))}
      </div>
    </div>
  );
});
