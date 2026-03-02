/**
 * AlertStore.ts
 * ──────────────────────────────────────────────
 * Maintains the active alert list independently of frame rendering.
 *
 * RULES:
 * - Tracks warning, danger, and struggling (attention + struggling behavior) states.
 * - Sorted: danger → struggling → warning.
 * - Creates alerts from both state_change events AND frame data (fallback).
 * - Auto-removes tracks that return to safe.
 * - Prevents stale alerts from persisting on recovery.
 */

import type { ActiveAlert } from '../types/detection';
import { wsClient } from '../core/websocket/WebSocketClient';

// ── Alarm sound controller ──────────────────────────────────────────────────
const AlarmController = (() => {
  let audio: HTMLAudioElement | null = null;
  let playing = false;

  function _getAudio(): HTMLAudioElement {
    if (!audio) {
      audio = new Audio('/sounds/alarm.mp3');
      audio.loop = true;
    }
    return audio;
  }

  return {
    start() {
      if (playing) return;
      const a = _getAudio();
      a.currentTime = 0;
      a.play().catch(() => { /* blocked until first user gesture */ });
      playing = true;
    },
    stop() {
      if (!playing) return;
      const a = _getAudio();
      a.pause();
      a.currentTime = 0;
      playing = false;
    },
  };
})();

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
          // 'safe' → fully resolved; clear the alert.
          if (this.alerts.has(person_id)) {
            this.alerts.delete(person_id);
            this._notify();
          }
        }
        // Note: 'attention' state is handled via frame data (behavior-aware)
      }

      // Also sync from frame data – create missing alerts + enrich existing
      if (msg.type === 'frame') {
        let changed = false;
        msg.persons.forEach((p) => {
          const existing = this.alerts.get(p.id);

          // Determine if this person should have an active alert
          const isStruggling = p.behavior === 'struggling';
          const isAlertable =
            p.status === 'warning' ||
            p.status === 'danger' ||
            (p.status === 'attention' && isStruggling);

          if (isAlertable) {
            // Determine alert state: prefer struggling label when behavior matches
            const alertState: 'warning' | 'danger' | 'struggling' =
              p.status === 'danger'
                ? 'danger'
                : isStruggling
                ? 'struggling'
                : 'warning';

            if (!existing) {
              // Create alert from frame data (fallback for missed state_change events)
              this.alerts.set(p.id, {
                trackId: p.id,
                state: alertState,
                confidence: p.confidence,
                framesUnderwater: p.frames_underwater,
                behavior: p.behavior,
                detectedAt: Date.now(),
              });
              changed = true;
            } else {
              // Enrich existing alert with latest frame data
              const updated: ActiveAlert = {
                ...existing,
                state: alertState,
                confidence: p.confidence,
                framesUnderwater: p.frames_underwater,
                behavior: p.behavior,
              };
              this.alerts.set(p.id, updated);
              changed = true;
            }
          } else if (existing) {
            if (p.status === 'safe') {
              // Fully resolved – remove alert
              this.alerts.delete(p.id);
              changed = true;
            } else {
              // Keep enriching non-alertable states without removing
              const updated: ActiveAlert = {
                ...existing,
                confidence: p.confidence,
                framesUnderwater: p.frames_underwater,
                behavior: p.behavior,
              };
              this.alerts.set(p.id, updated);
              changed = true;
            }
          }
        });

        if (changed) this._notify();
      }
    });
  }

  private _notify() {
    const sorted = this._sorted();
    // Play alarm whenever there is at least one active alert; stop when all clear
    const hasActiveAlert = sorted.some(
      (a) => a.state === 'danger' || a.state === 'warning' || a.state === 'struggling'
    );
    if (hasActiveAlert) {
      AlarmController.start();
    } else {
      AlarmController.stop();
    }
    this.listeners.forEach((l) => l(sorted));
  }

  private _sorted(): ActiveAlert[] {
    const order: Record<string, number> = { danger: 0, struggling: 1, warning: 2 };
    return Array.from(this.alerts.values()).sort((a, b) => {
      const oa = order[a.state] ?? 3;
      const ob = order[b.state] ?? 3;
      if (oa !== ob) return oa - ob;
      return b.detectedAt - a.detectedAt;
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
