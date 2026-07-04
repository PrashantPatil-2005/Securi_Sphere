"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Theme = "dark" | "light";

const STORAGE_KEY = "securisphere-theme";
const REDUCED_MOTION_KEY = "securisphere-reduced-motion";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  reducedMotion: boolean;
  setReducedMotion: (enabled: boolean) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.classList.remove("dark", "light");
  document.documentElement.classList.add(theme);
}

function applyReducedMotion(enabled: boolean) {
  document.documentElement.setAttribute("data-reduced-motion", enabled ? "true" : "false");
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [reducedMotion, setReducedMotionState] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
    const resolved = stored === "light" ? "light" : "dark";
    setThemeState(resolved);
    applyTheme(resolved);

    const motionStored = localStorage.getItem(REDUCED_MOTION_KEY);
    const motionResolved =
      motionStored === "true"
        ? true
        : motionStored === "false"
          ? false
          : window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setReducedMotionState(motionResolved);
    applyReducedMotion(motionResolved);
  }, []);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    localStorage.setItem(STORAGE_KEY, next);
    applyTheme(next);
  }, []);

  const setReducedMotion = useCallback((enabled: boolean) => {
    setReducedMotionState(enabled);
    localStorage.setItem(REDUCED_MOTION_KEY, String(enabled));
    applyReducedMotion(enabled);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, [theme, setTheme]);

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme, reducedMotion, setReducedMotion }),
    [theme, setTheme, toggleTheme, reducedMotion, setReducedMotion],
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
