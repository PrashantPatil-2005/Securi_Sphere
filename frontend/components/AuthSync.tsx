"use client";

import { useEffect } from "react";
import { hasLocalToken, setAuthCookie } from "@/lib/auth/session";

/** Sync auth cookie for users who logged in before cookie-based middleware. */
export function AuthSync() {
  useEffect(() => {
    if (hasLocalToken()) setAuthCookie();
  }, []);
  return null;
}
