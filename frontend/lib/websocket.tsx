"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { WS_API_URL, fetchWsToken } from "./api";

export type WSMessage = {
  type: string;
  data: Record<string, unknown>;
};

type Listener = (msg: WSMessage) => void;

class WebSocketStore {
  private ws: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private connected = false;
  private statusListeners = new Set<() => void>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 50;
  private pingTimer: ReturnType<typeof setInterval> | null = null;

  subscribeStatus = (cb: () => void) => {
    this.statusListeners.add(cb);
    return () => {
      this.statusListeners.delete(cb);
    };
  };

  getSnapshot = () => this.connected;

  subscribe = (listener: Listener) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  private notifyStatus() {
    this.statusListeners.forEach((cb) => cb());
  }

  private emit(msg: WSMessage) {
    this.listeners.forEach((l) => l(msg));
  }

  connect() {
    if (typeof window === "undefined") return;
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;

    void fetchWsToken().then((token) => {
      if (!token) return;
      const wsUrl = WS_API_URL.replace("http", "ws") + `/api/v1/ws`;
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: "auth", token }));
        this.connected = true;
        this.reconnectAttempts = 0;
        this.notifyStatus();
        this.startPing();
      };
      this.ws = ws;
      ws.onclose = () => {
        this.connected = false;
        this.stopPing();
        this.notifyStatus();
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        this.reconnectAttempts = Math.min(this.reconnectAttempts + 1, this.maxReconnectAttempts);
        this.reconnectTimer = setTimeout(() => this.connect(), delay);
      };
      ws.onmessage = (ev) => {
        try {
          this.emit(JSON.parse(ev.data) as WSMessage);
        } catch {
          /* ignore */
        }
      };
    });
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.stopPing();
    this.ws?.close();
    this.ws = null;
    this.connected = false;
    this.reconnectAttempts = 0;
    this.notifyStatus();
  }

  private startPing() {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 30_000);
  }

  private stopPing() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
}

const store = new WebSocketStore();

/**
 * Targeted WS invalidation map.
 *
 * Each message type maps to the specific query key prefixes that actually
 * need refreshing. React Query invalidates all queries whose key starts
 * with the given prefix (prefix matching).
 *
 * Dashboard SIEM query keys (all under ["siem", "<endpoint>", ...]):
 *   - executive       → SecurityKpis + AlertTrendChart
 *   - severity-distribution → SeverityBreakdown
 *   - top-risky-hosts → HostRiskPanel
 *   - attack-timelines → AttackTimelines
 *
 * Removed: broad ["siem"] prefix that was causing all 5 SIEM dashboard
 * queries to refetch on every WS message type.
 */
const INVALIDATION_BY_TYPE: Record<string, readonly (readonly string[])[]> = {
  // Raw events: update executive summary (total_events) and attack timelines
  // (which include event details). Do NOT refresh severity-distribution
  // (alerts only) or top-risky-hosts (threat scores, not events).
  new_event: [["siem", "executive"], ["siem", "attack-timelines"]],
  // New alert: update alert lists, executive summary (active/critical counts),
  // and severity distribution. Do NOT refresh top-risky-hosts or timelines.
  new_alert: [["alerts"], ["siem", "executive"], ["siem", "severity-distribution"]],
  // Alert updated (status, assignment, etc.): same as new_alert
  alert_updated: [["alerts"], ["siem", "executive"], ["siem", "severity-distribution"]],
  // Alert resolved: same as new_alert
  alert_resolved: [["alerts"], ["siem", "executive"], ["siem", "severity-distribution"]],
  // Alert feedback: only alert detail/investigation queries (no dashboard analytics)
  alert_feedback: [["alerts"]],
  // Host status change: update host lists, executive summary (online_hosts),
  // and top-risky-hosts (host risk scores depend on host status).
  host_status: [["hosts"], ["siem", "executive"], ["siem", "top-risky-hosts"]],
  // New host enrolled: update host lists and executive summary (total_hosts)
  host_enrolled: [["hosts"], ["siem", "executive"]],
  // Offenses (backend does not emit these yet; forward compatibility)
  new_offense: [["offenses"]],
  offense_updated: [["offenses"]],
  // Incidents (backend does not emit these yet; forward compatibility)
  new_incident: [["incidents"]],
  incident_updated: [["incidents"]],
  incident_status_changed: [["incidents"]],
  // security_feed: real-time events flow directly to LiveFeed via
  // useSecurityFeedStore (no HTTP needed). Only invalidate the executive
  // summary so KPIs eventually reflect new event counts.
  security_feed: [["siem", "executive"]],
};

/**
 * Throttle interval for batching WS-triggered query invalidations.
 *
 * Previous 600ms debounce allowed ~1.7 flushes/sec under continuous
 * traffic, causing repeated HTTP requests every ~600ms.
 *
 * 2-second throttle means at most 1 flush per 2 seconds regardless of
 * incoming WS message rate. Multiple events arriving within the window
 * are coalesced into a single invalidation batch with deduplicated keys.
 *
 * LiveFeed messages bypass this entirely — they flow directly through
 * useSecurityFeedStore → useSyncExternalStore, never touching the
 * invalidation pipeline.
 */
const INVALIDATION_THROTTLE_MS = 2_000;

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  useEffect(() => {
    store.connect();

    const pending = new Set<string>();
    let timer: ReturnType<typeof setTimeout> | null = null;
    let lastFlushAt = 0;

    const flush = () => {
      timer = null;
      lastFlushAt = Date.now();
      const keys = Array.from(pending);
      pending.clear();
      for (const serialized of keys) {
        const queryKey = JSON.parse(serialized) as string[];
        queryClient.invalidateQueries({ queryKey });
      }
    };

    const scheduleInvalidation = (queryKey: readonly string[]) => {
      pending.add(JSON.stringify(queryKey));
      if (timer) return; // already scheduled — coalesce

      const elapsed = Date.now() - lastFlushAt;
      if (elapsed >= INVALIDATION_THROTTLE_MS) {
        // Enough time has passed — flush immediately
        flush();
      } else {
        // Schedule a flush for when the throttle window expires
        timer = setTimeout(flush, INVALIDATION_THROTTLE_MS - elapsed);
      }
    };

    const unsub = store.subscribe((msg) => {
      const targets = INVALIDATION_BY_TYPE[msg.type];
      if (!targets) return;
      for (const queryKey of targets) scheduleInvalidation(queryKey);

      // Targeted invalidation: if the event carries an alert ID, also
      // refresh that specific alert's detail/investigation queries so
      // the analyst's current view updates without a full list refetch.
      const alertId = msg.data?.id;
      if (typeof alertId === "string" && targets.some((k) => k[0] === "alerts")) {
        scheduleInvalidation(["alerts", "detail", alertId]);
        scheduleInvalidation(["alerts", "investigation", alertId]);
      }
    });

    return () => {
      unsub();
      if (timer) clearTimeout(timer);
      store.disconnect();
    };
  }, [queryClient]);

  return <>{children}</>;
}

export function useWsConnected() {
  return useSyncExternalStore(store.subscribeStatus, store.getSnapshot, () => false);
}

/** Subscribe to specific WS message types without re-rendering unrelated components. */
export function useWsMessages(types: string[], onMessage: (msg: WSMessage) => void) {
  const typesKey = types.join(",");
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  useEffect(() => {
    const typeSet = new Set(typesKey.split(","));
    return store.subscribe((msg) => {
      if (typeSet.has(msg.type)) handlerRef.current(msg);
    });
  }, [typesKey]);
}


export function useSecurityFeedStore(maxItems = 50) {
  const feedRef = useRef<Array<Record<string, unknown>>>([]);
  const listenersRef = useRef(new Set<() => void>());

  const subscribe = useCallback((cb: () => void) => {
    listenersRef.current.add(cb);
    return () => listenersRef.current.delete(cb);
  }, []);

  const getSnapshot = useCallback(() => feedRef.current, []);

  useWsMessages(["security_feed", "new_alert"], (msg) => {
    const item = { ...msg.data, _type: msg.type, _ts: Date.now() };
    feedRef.current = [item, ...feedRef.current].slice(0, maxItems);
    listenersRef.current.forEach((l) => l());
  });

  const prepend = useCallback((items: Array<Record<string, unknown>>) => {
    feedRef.current = [...items, ...feedRef.current].slice(0, maxItems);
    listenersRef.current.forEach((l) => l());
  }, [maxItems]);

  return { subscribe, getSnapshot, prepend };
}

export function useFeedItems(
  subscribe: (cb: () => void) => () => void,
  getSnapshot: () => WSMessage["data"][],
) {
  return useSyncExternalStore(subscribe, getSnapshot, () => []);
}
