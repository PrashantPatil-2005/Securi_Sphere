"use client";

import { useState, useRef, useEffect, useCallback, type ReactNode } from "react";
import { cn } from "@/lib/utils/cn";

interface DropdownItem {
  label: string;
  value?: string;
  icon?: ReactNode;
  onClick?: () => void;
  danger?: boolean;
  separator?: boolean;
  disabled?: boolean;
}

interface DropdownProps {
  trigger: ReactNode;
  items: DropdownItem[];
  align?: "left" | "right";
  className?: string;
  width?: string;
}

export function Dropdown({
  trigger,
  items,
  align = "right",
  className,
  width = "min-w-[12rem]",
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (ref.current && !ref.current.contains(e.target as Node)) {
      setOpen(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, handleClickOutside]);

  return (
    <div ref={ref} className={cn("relative inline-block", className)}>
      <div onClick={() => setOpen((v) => !v)}>{trigger}</div>
      {open && (
        <div
          className={cn(
            "dropdown-menu animate-scale-in",
            align === "left" ? "left-0" : "right-0",
            width,
          )}
          role="menu"
        >
          {items.map((item, i) =>
            item.separator ? (
              <div key={i} className="dropdown-separator" />
            ) : (
              <button
                key={i}
                type="button"
                role="menuitem"
                disabled={item.disabled}
                onClick={() => {
                  item.onClick?.();
                  setOpen(false);
                }}
                className={cn(
                  "dropdown-item w-full text-left",
                  item.danger && "text-danger hover:bg-danger/10",
                  item.disabled && "opacity-40 cursor-not-allowed",
                )}
              >
                {item.icon && (
                  <span className="shrink-0 [&>svg]:w-4 [&>svg]:h-4">{item.icon}</span>
                )}
                {item.label}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}

export function DropdownTrigger({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={cn("inline-flex", className)}>{children}</span>;
}
