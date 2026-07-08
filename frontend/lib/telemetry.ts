import { api } from "./api";

const SESSION_KEY = "securi_telemetry_session";

let telemetryEnabled: boolean | null = null;

export function setTelemetryEnabled(enabled: boolean) {
  telemetryEnabled = enabled;
}

export function getTelemetrySessionId(): string {
  if (typeof window === "undefined") return "";
  let id = sessionStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

/** Fire-and-forget product telemetry. Swallows errors. */
export function track(event: string, properties?: Record<string, unknown>) {
  if (typeof window === "undefined") return;
  if (telemetryEnabled === false) return;

  void api("/api/v1/telemetry/events", {
    method: "POST",
    body: JSON.stringify({
      event,
      properties,
      session_id: getTelemetrySessionId(),
      page_path: window.location.pathname,
    }),
  }).catch(() => {});
}

const pending: Array<{ event: string; properties?: Record<string, unknown> }> = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;

/** Batched track for high-frequency events (e.g. dwell time). */
export function trackBatched(event: string, properties?: Record<string, unknown>) {
  pending.push({ event, properties });
  if (!flushTimer) {
    flushTimer = setTimeout(() => {
      flushTimer = null;
      const batch = pending.splice(0, pending.length);
      for (const item of batch) track(item.event, item.properties);
    }, 800);
  }
}
