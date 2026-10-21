import { clearAuthCookie, setAuthCookie } from "./auth/session";

/** Browser uses same-origin requests (Next.js rewrites to the backend). */
const API_URL =
  typeof window !== "undefined"
    ? ""
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * In-memory bearer token, populated after a successful login/register so that
 * authenticated requests (e.g. /api/v1/auth/me) can be authorised via the
 * `Authorization: Bearer` header. get_current_user on the backend checks the
 * header before falling back to the HttpOnly access_token cookie, so this
 * keeps sessions working even if the cookie is not set by the backend.
 */
let accessToken: string | null = null;

/** Call after a successful login/register to store the access token. */
export function setAccessToken(token: string | null) {
  accessToken = token;
}

/** Read the currently stored access token (if any). */
export function getAccessToken(): string | null {
  return accessToken;
}

/** WebSocket connects directly to the backend (not via Next rewrite). */
export function getWsApiUrl(): string {
  if (typeof window !== "undefined") {
    const scheme = window.location.protocol === "https:" ? "https" : "http";
    return `${scheme}://${window.location.hostname}:8000`;
  }
  return BACKEND_URL;
}

/** @deprecated Use getWsApiUrl() so browser hostname matches the page origin. */
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
  accessToken = null;
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
  const data = (await res.json().catch(() => null)) as { access_token?: string } | null;
  if (data?.access_token) setAccessToken(data.access_token);
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
      if (nested.code === "internal_error") {
        return "Something went wrong on the server. Please try again in a moment.";
      }
      if (typeof nested.message === "string" && nested.code !== "validation_error") {
        return nested.message;
      }
      const details = nested.details;
      if (Array.isArray(details) && details.length > 0) {
        const parts = details.map((d) => {
          if (!d || typeof d !== "object") return String(d);
          const item = d as Record<string, unknown>;
          const loc = Array.isArray(item.loc) ? item.loc.filter((x) => x !== "body").join(".") : "";
          const raw = typeof item.msg === "string" ? item.msg : String(item);
          // Pydantic prefixes custom validators with "Value error, " — show the real message.
          const msg = raw.startsWith("Value error, ") ? raw.slice("Value error, ".length) : raw;
          return loc ? `${loc}: ${msg}` : msg;
        });
        return parts.join("; ");
      }
      if (typeof nested.message === "string") return nested.message;
    }
  }
  if (status === 403) return "Insufficient permissions — admin or analyst role required";
  if (status === 429) return "Too many attempts. Please wait a few minutes and try again.";
  if (status === 401) return "Not logged in — please sign in again";
  if (status >= 500) return "Something went wrong on the server. Please try again in a moment.";
  return "Request failed";
}

/** HTTP-aware error so callers can branch on 401/403/404/5xx without parsing messages. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function errorStatus(err: unknown): number | undefined {
  return err instanceof ApiError ? err.status : undefined;
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
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
      signal: options.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(
      "Cannot reach the server. Make sure the backend is running on " + BACKEND_URL,
      0,
    );
  }

  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) {
      const retryRes = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
        credentials: "include",
        signal: options.signal,
      });
      if (!retryRes.ok) {
        const err = await retryRes.json().catch(() => null);
        throw new ApiError(parseApiError(err, retryRes.status), retryRes.status);
      }
      if (retryRes.status === 204) return {} as T;
      return retryRes.json();
    }
    redirectToLogin();
    throw new ApiError("Session expired", 401);
  }

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new ApiError(parseApiError(err, res.status), res.status);
  }

  if (res.status === 204) return {} as T;
  return res.json();
}

/** Like `api()` but returns the raw Response for binary downloads. Handles auth retry. */
export async function apiRaw(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
      signal: options.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(
      "Cannot reach the server. Make sure the backend is running on " + BACKEND_URL,
      0,
    );
  }

  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) {
      const retryRes = await fetch(`${API_URL}${path}`, {
        ...options,
        headers,
        credentials: "include",
        signal: options.signal,
      });
      if (!retryRes.ok) {
        const err = await retryRes.json().catch(() => null);
        throw new ApiError(parseApiError(err, retryRes.status), retryRes.status);
      }
      return retryRes;
    }
    redirectToLogin();
    throw new ApiError("Session expired", 401);
  }

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new ApiError(parseApiError(err, res.status), res.status);
  }

  return res;
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
