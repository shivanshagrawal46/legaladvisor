import { useEffect, useRef, useCallback } from "react";
import { WS_URL } from "./api";

export function useWebSocket({ onMessage, onOpen, onClose }) {
  const wsRef = useRef(null);
  const handlersRef = useRef({ onMessage, onOpen, onClose });
  handlersRef.current = { onMessage, onOpen, onClose };

  const connect = useCallback(() => {
    const state = wsRef.current?.readyState;
    // Guard against both OPEN (1) and CONNECTING (0) — React StrictMode
    // calls connect() twice in dev; without this guard two sockets are
    // created and every server message fires onMessage twice.
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => handlersRef.current.onOpen?.();
    ws.onclose = () => {
      // Only null the ref if it still points to THIS socket.
      // In React StrictMode the cleanup creates a second socket before
      // the first one's onclose fires — without this guard the second
      // socket's ref gets wiped and the auth token is never sent.
      if (wsRef.current === ws) wsRef.current = null;
      handlersRef.current.onClose?.();
    };
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        handlersRef.current.onMessage?.(data);
      } catch (_) {}
    };
  }, []);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  return { connect, send, disconnect, wsRef };
}
