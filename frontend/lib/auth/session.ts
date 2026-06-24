/** Cookie-based session marker for Next.js middleware (set only after /auth/me succeeds). */

export const AUTH_COOKIE = "ss_auth";

export function setAuthCookie() {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=604800; SameSite=Lax`;
}

export function clearAuthCookie() {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
  try {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  } catch {
    /* ignore */
  }
}
