/**
 * useWebSocket.ts
 * ──────────────────────────────────────────────
 * React hook that wraps WebSocketClient.
 * Exposes connection status to UI components.
 * Message handling is delegated to state stores – not React state.
 */

import { useEffect, useState, useCallback } from 'react';
import { wsClient, type WsClientStatus } from './WebSocketClient';
import type { WsMessage } from '../../types/detection';

interface UseWebSocketReturn {
  status: WsClientStatus;
  connect: (token: string) => void;
  disconnect: () => void;
  sendVideoPath: (videoPath: string) => void;
  /** Subscribe to raw messages without triggering re-renders */
  addRawListener: (handler: (msg: WsMessage) => void) => () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [status, setStatus] = useState<WsClientStatus>(wsClient.status);

  useEffect(() => {
    const unsub = wsClient.onStatus(setStatus);
    return () => { unsub(); };
  }, []);

  const connect = useCallback((token: string) => {
    wsClient.connect(token);
  }, []);

  const disconnect = useCallback(() => {
    wsClient.disconnect();
  }, []);

  const sendVideoPath = useCallback((videoPath: string) => {
    wsClient.startProcessing(videoPath);
  }, []);

  const addRawListener = useCallback((handler: (msg: WsMessage) => void) => {
    return wsClient.onMessage(handler);
  }, []);

  return { status, connect, disconnect, sendVideoPath, addRawListener };
}
