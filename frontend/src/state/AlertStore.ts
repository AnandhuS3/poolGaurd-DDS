/**
 * AlertStore.ts
 * ──────────────────────────────────────────────
 * Maintains the active and acknowledged alert lists independently of frame rendering.
 *
 * RULES:
 * - Tracks warning, danger, and struggling (attention + struggling behavior) states.
 * - Sorted: danger → struggling → warning.
 * - Creates alerts from both state_change events AND frame data (fallback).
 * - Auto-removes tracks that return to safe.
 * - Prevents stale alerts from persisting on recovery.
 * - Once processing is complete, frame/state_change events no longer create new alerts.
 * - Acknowledged alerts cannot be re-triggered within the same session.
 * - Calling clear() (new session) resets all state including acknowledged ids.
 */

import type { ActiveAlert, AcknowledgedAlert } from '../types/detection';
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
type AckAlertListener = (alerts: AcknowledgedAlert[]) => void;

class AlertStoreClass {
  private alerts: Map<number, ActiveAlert> = new Map();
  /** Acknowledged alerts ordered newest-first */
  private acknowledged: AcknowledgedAlert[] = [];
  /** Track IDs acknowledged this session – prevents re-creation from stale frames */
  private acknowledgedIds: Set<number> = new Set();
  /** Set to true on 'complete' – prevents new alerts from subsequent stale frame messages */
  private processingComplete: boolean = false;

  private listeners: Set<AlertListener> = new Set();
  private ackListeners: Set<AckAlertListener> = new Set();

  constructor() {
    wsClient.onMessage((msg) => {
      // ── New session started – reset complete flag ─────────────────────
      if (msg.type === 'video_info') {
        this.processingComplete = false;
        return;
      }

      // ── Processing done – lock against stale events ───────────────────
      if (msg.type === 'complete') {
        this.processingComplete = true;
        return;
      }

      // ── State-change events ───────────────────────────────────────────
      if (msg.type === 'state_change') {
        if (this.processingComplete) return;

        const { person_id, new_state, frames_underwater } = msg;
        const stateLower = new_state.toLowerCase() as 'safe' | 'warning' | 'danger' | 'attention';

        if (stateLower === 'warning' || stateLower === 'danger') {
          // Never re-create an alert for an acknowledged track
          if (this.acknowledgedIds.has(person_id)) return;

          const existing = this.alerts.get(person_id);
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
          if (this.alerts.has(person_id)) {
            this.alerts.delete(person_id);
            this._notify();
          }
        }
        // 'attention' state is handled via frame data (behavior-aware)
      }

      // ── Frame events (fallback alert creation + enrichment) ───────────
      if (msg.type === 'frame') {
        if (this.processingComplete) return;

        let changed = false;
        msg.persons.forEach((p) => {
          // Never create/update alerts for acknowledged tracks
          if (this.acknowledgedIds.has(p.id)) return;

          const existing = this.alerts.get(p.id);
          const isStruggling = p.behavior === 'struggling';
          const isAlertable =
            p.status === 'warning' ||
            p.status === 'danger' ||
            (p.status === 'attention' && isStruggling);

          if (isAlertable) {
            const alertState: 'warning' | 'danger' | 'struggling' =
              p.status === 'danger'
                ? 'danger'
                : isStruggling
                ? 'struggling'
                : 'warning';

            if (!existing) {
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
              this.alerts.set(p.id, {
                ...existing,
                state: alertState,
                confidence: p.confidence,
                framesUnderwater: p.frames_underwater,
                behavior: p.behavior,
              });
              changed = true;
            }
          } else if (existing) {
            if (p.status === 'safe') {
              this.alerts.delete(p.id);
              changed = true;
            } else {
              this.alerts.set(p.id, {
                ...existing,
                confidence: p.confidence,
                framesUnderwater: p.frames_underwater,
                behavior: p.behavior,
              });
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

  private _notifyAck() {
    this.ackListeners.forEach((l) => l([...this.acknowledged]));
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

  getAcknowledgedAlerts(): AcknowledgedAlert[] {
    return [...this.acknowledged];
  }

  subscribe(listener: AlertListener): () => void {
    this.listeners.add(listener);
    listener(this._sorted());
    return () => this.listeners.delete(listener);
  }

  subscribeAcknowledged(listener: AckAlertListener): () => void {
    this.ackListeners.add(listener);
    listener([...this.acknowledged]);
    return () => this.ackListeners.delete(listener);
  }

  /**
   * Acknowledge an active alert: moves it from the active list to the
   * acknowledged list, prevents re-creation from stale frames, and
   * stops the alarm if no active alerts remain.
   * Works regardless of whether video processing is still running.
   */
  dismiss(trackId: number) {
    // Mark as acknowledged first – blocks any in-flight frame/state_change handler
    // from re-creating this alert before we call _notify().
    this.acknowledgedIds.add(trackId);

    const alert = this.alerts.get(trackId);
    if (alert) {
      this.alerts.delete(trackId);
      this.acknowledged = [{ ...alert, acknowledgedAt: Date.now() }, ...this.acknowledged];
    }

    // Always stop the alarm immediately on ACK, regardless of other alert state.
    // _notify() will restart it only if genuinely unacknowledged active alerts remain.
    AlarmController.stop();
    this._notify();
    this._notifyAck();
  }

  /** Silence the audible alarm without removing or acknowledging alert cards. */
  silenceAlarm() {
    AlarmController.stop();
  }

  /** Clear all state – call at the start of a new session. */
  clear() {
    this.alerts.clear();
    this.acknowledged = [];
    this.acknowledgedIds.clear();
    this.processingComplete = false;
    AlarmController.stop();
    this._notify();
    this._notifyAck();
  }
}

export const AlertStore = new AlertStoreClass();

