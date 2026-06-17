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
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function refreshAccessToken(): Promise<string | null> {
  const tokens = getTokens();
  if (!tokens?.refresh_token) return null;
  const res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data: TokenPair = await res.json();
  setTokens(data);
  return data.access_token;
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

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.Authorization = `Bearer ${newToken}`;
      const retryRes = await fetch(`${API_URL}${path}`, { ...options, headers });
      if (!retryRes.ok) {
        const err = await retryRes.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(err.detail || "Request failed");
      }
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

export { API_URL };
