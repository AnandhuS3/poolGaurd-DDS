// ──────────────────────────────────────────────
// Detection / Person types (mirrors backend payload)
// ──────────────────────────────────────────────

export type DetectionState = 'safe' | 'warning' | 'danger' | 'attention';
export type DetectionStateUpper = 'SAFE' | 'WARNING' | 'DANGER' | 'ATTENTION';

export interface Person {
  id: number;
  /** [x1, y1, x2, y2] absolute pixel coordinates */
  bbox: [number, number, number, number];
  status: DetectionState;
  state: DetectionStateUpper;
  alert: boolean;
  frames_underwater: number;
  confidence: number;
  behavior: string;
  pose_available: boolean;
  lstm_risk_state: string;
  lstm_risk_scores: [number, number, number];
  lstm_confidence: number;
  lstm_available: boolean;
}

export interface FramePerformance {
  processing_fps: number;
  video_fps: number;
  frame_skip: number;
  speed_ratio: number;
  real_time: boolean;
}

export interface FrameSummary {
  total: number;
  safe: number;
  warning: number;
  danger: number;
  alerts: number;
}

// ──────────────────────────────────────────────
// WebSocket message types
// ──────────────────────────────────────────────

export interface WsFrameMessage {
  type: 'frame';
  analysis_frame: string; // base64 JPEG
  frame_number: number;
  total_frames: number;
  persons: Person[];
  performance: FramePerformance;
  summary: FrameSummary;
}

export interface WsStateChangeMessage {
  type: 'state_change';
  person_id: number;
  old_state: DetectionStateUpper;
  new_state: DetectionStateUpper;
  timestamp: number;
  frames_underwater: number;
}

export interface WsVideoInfoMessage {
  type: 'video_info';
  fps: number;
  total_frames: number;
  width: number;
  height: number;
}

export interface WsCompleteMessage {
  type: 'complete';
  message: string;
  total_persons: number;
  person_data: Record<string, unknown>;
  motion_stats?: string;
}

export interface WsErrorMessage {
  type: 'error';
  message: string;
}

export type WsMessage =
  | WsFrameMessage
  | WsStateChangeMessage
  | WsVideoInfoMessage
  | WsCompleteMessage
  | WsErrorMessage;

// ──────────────────────────────────────────────
// Alert types
// ──────────────────────────────────────────────

export interface ActiveAlert {
  trackId: number;
  state: 'warning' | 'danger' | 'struggling';
  confidence: number;
  framesUnderwater: number;
  behavior: string;
  detectedAt: number; // epoch ms
}

export interface AcknowledgedAlert extends ActiveAlert {
  /** Epoch ms when the operator acknowledged this alert */
  acknowledgedAt: number;
}

// ──────────────────────────────────────────────
// Auth types
// ──────────────────────────────────────────────

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  phone_number?: string;
  role: 'admin' | 'guard';
  is_active?: boolean;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  user: AuthUser;
}
