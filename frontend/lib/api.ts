import { clearAuthCookie, setAuthCookie } from "./auth/session";

/** Browser uses same-origin requests (Next.js rewrites to the backend). */
const API_URL =
  typeof window !== "undefined"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** WebSocket always connects directly to the backend (not via Next rewrite). */
export const WS_API_URL = BACKEND_URL;

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/** Verify HttpOnly session cookies work, then set middleware gate cookie. */
export async function establishSession(): Promise<void> {
  await api("/api/v1/auth/me");
  setAuthCookie();
}


export function clearTokens() {
  clearAuthCookie();
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const path = window.location.pathname;
  if (path.startsWith("/login") || path.startsWith("/register")) return;
  const next = path !== "/" ? `?next=${encodeURIComponent(path)}` : "";
  window.location.href = `/login${next}`;
}

async function refreshAccessToken(): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    clearTokens();
    return false;
  }
  setAuthCookie();
  return true;
}

export async function logoutApi(): Promise<void> {
  try {
    await fetch(`${API_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({}),
    });
  } catch {
    /* best effort */
  }
  clearTokens();
}

function parseApiError(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const o = body as Record<string, unknown>;
    if (typeof o.detail === "string") return o.detail;
    if (Array.isArray(o.detail)) return o.detail.map(String).join("; ");
    const nested = o.error as Record<string, unknown> | undefined;
    if (nested) {
      if (typeof nested.message === "string" && nested.code !== "validation_error") {
        return nested.message;
      }
      const details = nested.details;
      if (Array.isArray(details) && details.length > 0) {
        const parts = details.map((d) => {
          if (!d || typeof d !== "object") return String(d);
          const item = d as Record<string, unknown>;
          const loc = Array.isArray(item.loc) ? item.loc.filter((x) => x !== "body").join(".") : "";
          const msg = typeof item.msg === "string" ? item.msg : String(item);
          return loc ? `${loc}: ${msg}` : msg;
        });
        return parts.join("; ");
      }
      if (typeof nested.message === "string") return nested.message;
    }
  }
  if (status === 403) return "Insufficient permissions — admin or analyst role required";
  if (status === 401) return "Not logged in — please sign in again";
  if (status >= 500) return "Server error — check backend logs";
  return "Request failed";
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: "include" });
  } catch {
    throw new Error("Cannot reach the server. Make sure the backend is running on " + BACKEND_URL);
  }

  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) {
      const retryRes = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: "include" });
      if (!retryRes.ok) {
        const err = await retryRes.json().catch(() => null);
        throw new Error(parseApiError(err, retryRes.status));
      }
      if (retryRes.status === 204) return {} as T;
      return retryRes.json();
    }
    redirectToLogin();
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(parseApiError(err, res.status));
  }

  if (res.status === 204) return {} as T;
  return res.json();
}

export async function fetchWsToken(): Promise<string | null> {
  try {
    const data = await api<{ token: string }>("/api/v1/ws/token", { method: "POST" });
    return data.token;
  } catch {
    return null;
  }
}

export { API_URL };
