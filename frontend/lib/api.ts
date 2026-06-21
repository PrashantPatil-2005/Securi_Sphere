import { clearAuthCookie, setAuthCookie } from "./auth/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

function getTokens(): TokenPair | null {
  if (typeof window === "undefined") return null;
  const access = localStorage.getItem("access_token");
  const refresh = localStorage.getItem("refresh_token");
  if (!access || !refresh) return null;
  return { access_token: access, refresh_token: refresh };
}

export function setTokens(tokens: TokenPair) {
  localStorage.setItem("access_token", tokens.access_token);
  localStorage.setItem("refresh_token", tokens.refresh_token);
  setAuthCookie();
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  clearAuthCookie();
}

async function refreshAccessToken(): Promise<string | null> {
  const tokens = getTokens();
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(tokens?.refresh_token ? { refresh_token: tokens.refresh_token } : {}),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data: TokenPair = await res.json();
  setTokens(data);
  return data.access_token;
}

export async function logoutApi(): Promise<void> {
  const tokens = getTokens();
  try {
    await fetch(`${API_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(tokens?.refresh_token ? { refresh_token: tokens.refresh_token } : {}),
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
  const tokens = getTokens();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (tokens?.access_token) {
    headers.Authorization = `Bearer ${tokens.access_token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: "include" });
  } catch {
    throw new Error("Cannot reach the server. Make sure the backend is running on " + API_URL);
  }

  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`;
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
    return getTokens()?.access_token ?? null;
  }
}

export { API_URL };
