/** Cookie-based session marker for Next.js middleware (set only after /auth/me succeeds). */

export const AUTH_COOKIE = "ss_auth";

function isSecureContext(): boolean {
  if (typeof window === "undefined") return false;
  return window.location.protocol === "https:";
}

export function setAuthCookie() {
  if (typeof document === "undefined") return;
  const secure = isSecureContext() ? "; Secure" : "";
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=604800; SameSite=Lax${secure}`;
}

export function clearAuthCookie() {
  if (typeof document === "undefined") return;
  const secure = isSecureContext() ? "; Secure" : "";
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; SameSite=Lax${secure}`;
}
