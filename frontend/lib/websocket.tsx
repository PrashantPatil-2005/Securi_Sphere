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
      };
      this.ws = ws;

      ws.onopen = () => {
        this.connected = true;
        this.notifyStatus();
      };
      ws.onclose = () => {
        this.connected = false;
        this.notifyStatus();
        this.reconnectTimer = setTimeout(() => this.connect(), 3000);
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
    this.ws?.close();
    this.ws = null;
    this.connected = false;
    this.notifyStatus();
  }
}

const store = new WebSocketStore();

/** Map WS message types to the query families that actually need refetching. */
const INVALIDATION_BY_TYPE: Record<string, readonly (readonly string[])[]> = {
  new_event: [["events"], ["siem"]],
  new_alert: [["alerts"], ["siem"]],
  alert_resolved: [["alerts"], ["siem"]],
  host_status: [["hosts"], ["siem"]],
  host_enrolled: [["hosts"], ["siem"]],
  // security_feed is handled by useSecurityFeedStore — no query invalidation
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

/** @deprecated Use useWsConnected + query invalidation instead */
export function useWebSocket(onMessage?: (msg: WSMessage) => void) {
  const connected = useWsConnected();
  useWsMessages(["new_alert", "new_event", "security_feed", "alert_resolved", "host_status"], (msg) => {
    onMessage?.(msg);
  });
  return { connected };
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
