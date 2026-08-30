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

/** Map WS message types to the query families that actually need refetching. */
const INVALIDATION_BY_TYPE: Record<string, readonly (readonly string[])[]> = {
  new_event: [["events"], ["siem"]],
  new_alert: [["alerts"], ["siem"]],
  alert_updated: [["alerts"], ["siem"]],
  alert_resolved: [["alerts"], ["siem"]],
  alert_feedback: [["alerts"]],
  host_status: [["hosts"], ["siem"]],
  host_enrolled: [["hosts"], ["siem"]],
  // Offenses — backend does not emit these yet; entries added for forward compatibility.
  new_offense: [["offenses"]],
  offense_updated: [["offenses"]],
  // Incidents — backend does not emit these yet; entries added for forward compatibility.
  new_incident: [["incidents"]],
  incident_updated: [["incidents"]],
  incident_status_changed: [["incidents"]],
  // security_feed carries real-time events; also invalidate the events list
  // so the analyst's view stays current. Debouncing (600ms) prevents
  // excessive refetches during burst ingestion.
  security_feed: [["events"], ["siem"]],
};

const INVALIDATION_DEBOUNCE_MS = 600;

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  useEffect(() => {
    store.connect();

    const pending = new Set<string>();
    let timer: ReturnType<typeof setTimeout> | null = null;

    const flush = () => {
      timer = null;
      const keys = Array.from(pending);
      pending.clear();
      for (const serialized of keys) {
        const queryKey = JSON.parse(serialized) as string[];
        queryClient.invalidateQueries({ queryKey });
      }
    };

    const scheduleInvalidation = (queryKey: readonly string[]) => {
      pending.add(JSON.stringify(queryKey));
      if (!timer) timer = setTimeout(flush, INVALIDATION_DEBOUNCE_MS);
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
