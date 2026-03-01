/**
 * AlertStore.ts
 * ──────────────────────────────────────────────
 * Maintains the active alert list independently of frame rendering.
 *
 * RULES:
 * - Only tracks warning + danger states.
 * - Sorted: danger first, then warning.
 * - Auto-removes tracks that return to safe.
 * - Prevents duplicate alerts per track per state.
 * - Handles state transitions: safe → warning → danger → safe.
 */

import type { ActiveAlert } from '../types/detection';
import { wsClient } from '../core/websocket/WebSocketClient';

type AlertListener = (alerts: ActiveAlert[]) => void;

class AlertStoreClass {
  private alerts: Map<number, ActiveAlert> = new Map();
  private listeners: Set<AlertListener> = new Set();

  constructor() {
    // Listen for state_change events from the WebSocket
    wsClient.onMessage((msg) => {
      if (msg.type === 'state_change') {
        const { person_id, new_state, frames_underwater } = msg;
        const stateLower = new_state.toLowerCase() as 'safe' | 'warning' | 'danger' | 'attention';

        if (stateLower === 'warning' || stateLower === 'danger') {
          const existing = this.alerts.get(person_id);

          // Prevent duplicate alert for same track + same state
          if (existing && existing.state === stateLower) return;

          this.alerts.set(person_id, {
            trackId: person_id,
            state: stateLower as 'warning' | 'danger',
            confidence: 0,
            framesUnderwater: frames_underwater,
            behavior: 'unknown',
            detectedAt: Date.now(),
          });

          this._notify();
        } else if (stateLower === 'safe') {
          // Track returned to safe – remove alert
          if (this.alerts.has(person_id)) {
            this.alerts.delete(person_id);
            this._notify();
          }
        }
      }

      // Also sync from frame data – enrich alert with confidence/behavior
      if (msg.type === 'frame') {
        let changed = false;
        msg.persons.forEach((p) => {
          const existing = this.alerts.get(p.id);
          if (existing) {
            // Update enrichment data without overriding detection state
            const updated: ActiveAlert = {
              ...existing,
              confidence: p.confidence,
              framesUnderwater: p.frames_underwater,
              behavior: p.behavior,
            };
            this.alerts.set(p.id, updated);
            changed = true;
          }

          // Auto-resolve alerts for tracks now in safe state
          if (p.status === 'safe' && this.alerts.has(p.id)) {
            this.alerts.delete(p.id);
            changed = true;
          }
        });

        if (changed) this._notify();
      }
    });
  }

  private _notify() {
    const sorted = this._sorted();
    this.listeners.forEach((l) => l(sorted));
  }

  private _sorted(): ActiveAlert[] {
    return Array.from(this.alerts.values()).sort((a, b) => {
      if (a.state === b.state) return b.detectedAt - a.detectedAt;
      return a.state === 'danger' ? -1 : 1;
    });
  }

  getAlerts(): ActiveAlert[] {
    return this._sorted();
  }

  subscribe(listener: AlertListener): () => void {
    this.listeners.add(listener);
    listener(this._sorted()); // immediate call
    return () => this.listeners.delete(listener);
  }

  clear() {
    this.alerts.clear();
    this._notify();
  }
}

export const AlertStore = new AlertStoreClass();
