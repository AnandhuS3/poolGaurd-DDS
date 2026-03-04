/**
 * WebSocketClient.ts
 * ──────────────────────────────────────────────
 * Raw WebSocket manager.
 * - Singleton per endpoint URL
 * - Auto-reconnects with exponential back-off
 * - Prevents duplicate connections
 * - Parses JSON safely and logs raw payloads in dev
 * - Emits structured messages to registered subscribers only
 *
 * ⚠️  NO React imports here. This is pure TS.
 */

import type { WsMessage } from '../../types/detection';

type MessageHandler = (msg: WsMessage) => void;
type StatusHandler = (status: WsClientStatus) => void;

export type WsClientStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'disconnected'
  | 'error';

// In dev, the Vite proxy forwards /ws to localhost:8000, so we
// connect to the current page's host.
// In production, VITE_API_URL = 'https://your-backend.railway.app', so
// we swap the protocol to wss://.
function resolveWsBase(): string {
  const apiUrl = import.meta.env.VITE_API_URL as string | undefined;
  if (apiUrl) {
    // https://... → wss://...  |  http://... → ws://...
    return apiUrl.replace(/^https/, 'wss').replace(/^http/, 'ws').replace(/\/$/, '');
  }
  // Dev: same origin, proxy handles it
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}`;
}

const BASE_URL = resolveWsBase();
const WS_PATH = '/ws/process';
const MAX_RETRIES = 8;
const BASE_DELAY_MS = 1000;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private token: string | null = null;
  private retryCount = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  private messageHandlers: Set<MessageHandler> = new Set();
  private statusHandlers: Set<StatusHandler> = new Set();
  private _status: WsClientStatus = 'idle';

  // ── Status management ──────────────────────────────────────────────────

  private setStatus(s: WsClientStatus) {
    this._status = s;
    this.statusHandlers.forEach((h) => h(s));
  }

  get status(): WsClientStatus {
    return this._status;
  }

  // ── Subscription API ──────────────────────────────────────────────────

  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler) {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  // ── Connection ─────────────────────────────────────────────────────────

  connect(token: string) {
    // Prevent duplicate connections
    if (
      this.socket &&
      (this.socket.readyState === WebSocket.OPEN ||
        this.socket.readyState === WebSocket.CONNECTING)
    ) {
      console.debug('[WS] Already connected or connecting – skipping duplicate connect');
      return;
    }

    this.token = token;
    this.intentionalClose = false;
    this._openSocket();
  }

  private _openSocket() {
    if (!this.token) return;

    const url = `${BASE_URL}${WS_PATH}?token=${encodeURIComponent(this.token)}`;
    console.debug('[WS] Connecting to', url);
    this.setStatus(this.retryCount === 0 ? 'connecting' : 'reconnecting');

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.info('[WS] Connected');
      this.retryCount = 0;
      this.setStatus('connected');
    };

    this.socket.onmessage = (event: MessageEvent) => {
      // Log raw payload in development for debug requirement
      if (import.meta.env.DEV) {
        // Only log non-frame types to avoid console spam
        try {
          const preview = JSON.parse(event.data as string);
          if (preview?.type !== 'frame') {
            console.debug('[WS] RAW payload:', preview);
          }
        } catch {
          // ignore parse log errors
        }
      }

      let msg: WsMessage | null = null;
      try {
        msg = JSON.parse(event.data as string) as WsMessage;
      } catch (err) {
        console.error('[WS] JSON parse error:', err, 'raw:', event.data);
        return;
      }

      // Log incoming state values per debug requirement
      if (msg.type === 'frame' && import.meta.env.DEV) {
        msg.persons.forEach((p) => {
          console.debug(`[WS] Person #${p.id} state=${p.state} status=${p.status} conf=${p.confidence.toFixed(2)}`);
        });
      }

      // Distribute to all subscribers
      this.messageHandlers.forEach((h) => h(msg!));
    };

    this.socket.onerror = (e) => {
      console.error('[WS] Socket error:', e);
      this.setStatus('error');
    };

    this.socket.onclose = (e) => {
      console.warn('[WS] Closed — code:', e.code, 'reason:', e.reason);

      if (this.intentionalClose) {
        this.setStatus('disconnected');
        return;
      }

      if (this.retryCount < MAX_RETRIES) {
        const delay = Math.min(BASE_DELAY_MS * 2 ** this.retryCount, 30_000);
        console.info(`[WS] Reconnecting in ${delay}ms (attempt ${this.retryCount + 1}/${MAX_RETRIES})`);
        this.retryCount++;
        this.setStatus('reconnecting');
        this.retryTimer = setTimeout(() => this._openSocket(), delay);
      } else {
        console.error('[WS] Max retries exceeded');
        this.setStatus('disconnected');
      }
    };
  }

  disconnect() {
    this.intentionalClose = true;
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    this.retryCount = 0;
    this.setStatus('idle');
  }

  /** Send a JSON payload to the backend */
  send(payload: Record<string, unknown>) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    } else {
      console.warn('[WS] Cannot send – socket not open. State:', this.socket?.readyState);
    }
  }

  /** Kick off processing for an uploaded file */
  startProcessing(videoPath: string) {
    this.send({ video_path: videoPath });
  }
}

// Single shared instance – prevents duplicate connections across the app
export const wsClient = new WebSocketClient();
