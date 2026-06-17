export const PAGE_SIZES = [25, 50, 100, 500] as const;

export const SORT_OPTIONS = [
  { value: "newest", label: "Newest First" },
  { value: "oldest", label: "Oldest First" },
  { value: "severity", label: "Severity" },
  { value: "risk_score", label: "Risk Score" },
  { value: "host_name", label: "Host Name" },
  { value: "alert_count", label: "Alert Count" },
] as const;

export function buildQuery(
  base: Record<string, string | number | boolean | undefined | null>,
  timeParams: Record<string, string>,
): string {
  const params = new URLSearchParams();
  Object.entries({ ...timeParams, ...base }).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const s = params.toString();
  return s ? `?${s}` : "";
}
