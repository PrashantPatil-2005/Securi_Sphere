"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL } from "./api";

type WSMessage = {
  type: string;
  data: Record<string, unknown>;
};

export function useWebSocket(onMessage?: (msg: WSMessage) => void) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const wsUrl = API_URL.replace("http", "ws") + `/api/v1/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as WSMessage;
        onMessageRef.current?.(msg);
      } catch {
        /* ignore */
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { connected };
}
