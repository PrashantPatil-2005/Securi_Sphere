/** Cookie-based session marker for middleware (localStorage tokens remain primary). */

export const AUTH_COOKIE = "ss_auth";

export function setAuthCookie() {
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=604800; SameSite=Lax`;
}

export function clearAuthCookie() {
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0; SameSite=Lax`;
}

export function hasLocalToken(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}
