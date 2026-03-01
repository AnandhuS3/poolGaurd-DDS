/**
 * DetectionStore.ts
 * ──────────────────────────────────────────────
 * Lightweight singleton store for detection state.
 *
 * DESIGN RULES:
 * - State is NOT stored in React – components read via subscriptions.
 * - Only updated on detection STATE CHANGES, not per-frame.
 * - Frame data (persons, frame image) is for the canvas layer only via refs.
 * - Does NOT override backend detection states.
 *
 * Future: Replace with Zustand/Redux if multi-camera support is added.
 */

import type {
  Person,
  FramePerformance,
  FrameSummary,
  WsVideoInfoMessage,
  WsFrameMessage,
} from '../types/detection';
import { wsClient } from '../core/websocket/WebSocketClient';

export interface DetectionState {
  isProcessing: boolean;
  isComplete: boolean;
  videoInfo: WsVideoInfoMessage | null;
  frameNumber: number;
  totalFrames: number;
  /** Latest persons array – updated every frame but kept for canvas */
  persons: Person[];
  /** Latest base64 JPEG frame image */
  frameImage: string | null;
  performance: FramePerformance | null;
  summary: FrameSummary | null;
  error: string | null;
}

type DetectionListener = (state: DetectionState) => void;

const initialState: DetectionState = {
  isProcessing: false,
  isComplete: false,
  videoInfo: null,
  frameNumber: 0,
  totalFrames: 0,
  persons: [],
  frameImage: null,
  performance: null,
  summary: null,
  error: null,
};

class DetectionStoreClass {
  private state: DetectionState = { ...initialState };
  private listeners: Set<DetectionListener> = new Set();

  // ── Frame cache (not in state – canvas reads directly from this) ───────
  /** Updated every frame, read by canvas via ref – zero React renders */
  public latestFrame: WsFrameMessage | null = null;

  constructor() {
    // Subscribe to WebSocket messages at store level
    wsClient.onMessage((msg) => {
      switch (msg.type) {
        case 'video_info':
          this._update({
            videoInfo: msg,
            totalFrames: msg.total_frames,
            isProcessing: true,
            isComplete: false,
            error: null,
          });
          break;

        case 'frame':
          // Update latestFrame for canvas rendering (no React state update)
          this.latestFrame = msg;

          // Only update React state on summary/progress changes (not per person)
          this._update({
            frameNumber: msg.frame_number,
            totalFrames: msg.total_frames,
            persons: msg.persons,
            frameImage: msg.analysis_frame,
            performance: msg.performance,
            summary: msg.summary,
            isProcessing: true,
          });
          break;

        case 'state_change':
          // Logged by WebSocketClient already; AlertStore handles this
          console.info(
            `[DetectionStore] State change – Person #${msg.person_id}: ${msg.old_state} → ${msg.new_state}`
          );
          break;

        case 'complete':
          this._update({
            isProcessing: false,
            isComplete: true,
          });
          break;

        case 'error':
          this._update({
            isProcessing: false,
            error: msg.message,
          });
          break;
      }
    });
  }

  private _update(partial: Partial<DetectionState>) {
    this.state = { ...this.state, ...partial };
    this.listeners.forEach((l) => l(this.state));
  }

  getState(): DetectionState {
    return this.state;
  }

  reset() {
    this.latestFrame = null;
    this._update({ ...initialState });
  }

  subscribe(listener: DetectionListener): () => void {
    this.listeners.add(listener);
    listener(this.state); // immediate call with current state
    return () => this.listeners.delete(listener);
  }
}

export const DetectionStore = new DetectionStoreClass();
