"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils/cn";

interface SearchBarProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSearch?: (value: string) => void;
  onClear?: () => void;
  className?: string;
  autoFocus?: boolean;
  size?: "sm" | "md";
}

export function SearchBar({
  placeholder = "Search\u2026",
  value: controlledValue,
  onChange,
  onSearch,
  onClear,
  className,
  autoFocus,
  size = "md",
}: SearchBarProps) {
  const [internalValue, setInternalValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const value = controlledValue !== undefined ? controlledValue : internalValue;

  const handleChange = useCallback(
    (v: string) => {
      setInternalValue(v);
      onChange?.(v);
    },
    [onChange],
  );

  const handleClear = useCallback(() => {
    setInternalValue("");
    onChange?.("");
    onClear?.();
    inputRef.current?.focus();
  }, [onChange, onClear]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        onSearch?.(value);
      }
      if (e.key === "Escape") {
        handleClear();
      }
    },
    [onSearch, value, handleClear],
  );

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  return (
    <div className={cn("search-bar", size === "sm" && "text-sm", className)}>
      <Search className="search-bar-icon w-4 h-4" />
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={cn(size === "sm" && "!py-1.5 !text-xs")}
        aria-label={placeholder}
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-foreground transition-colors"
          aria-label="Clear search"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
