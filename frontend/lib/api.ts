import { clearAuthCookie, setAuthCookie } from "./auth/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

/** Cookie-primary auth: HttpOnly cookies carry session; tokens in body used only to sync cookie gate. */
export function setTokens(tokens: TokenPair) {
  void tokens;
  setAuthCookie();
}

export function clearTokens() {
  clearAuthCookie();
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
    throw new Error("Cannot reach the server. Make sure the backend is running on " + API_URL);
  }

  if (res.status === 401 && retry) {
    const ok = await refreshAccessToken();
    if (ok) {
      const retryRes = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: "include" });
      if (!retryRes.ok) {
        const err = await retryRes.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || "Request failed");
      }
      if (retryRes.status === 204) return {} as T;
      return retryRes.json();
    }
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || "Request failed");
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
