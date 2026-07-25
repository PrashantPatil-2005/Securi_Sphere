import { apiRaw } from "./api";

/** Download a file from the API using cookie-based auth with automatic token refresh. */
export async function downloadAuthenticated(path: string, filename: string): Promise<void> {
  const res = await apiRaw(path, { method: "GET" }, false);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
