/**
 * Dashboard.tsx
 * Main surveillance view: Video feed (left) + Alert panel (right).
 *
 * RULES:
 * - Video feed updates via rAF inside VideoCanvas – not React re-renders.
 * - Alert panel updates only on state changes via AlertStore subscription.
 * - DetectionStore drives progress/summary via minimal state updates.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { VideoCanvas } from '../components/video/VideoCanvas';
import { AlertPanel } from '../components/alerts/AlertPanel';
import { DetectionStore, type DetectionState } from '../state/DetectionStore';
import { AlertStore } from '../state/AlertStore';
import { wsClient } from '../core/websocket/WebSocketClient';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useRef } from 'react';

export function Dashboard() {
  const navigate = useNavigate();
  const { token } = useAuth();
  const autoConnectAttempted = useRef(false);
  const [detection, setDetection] = useState<DetectionState>(() =>
    DetectionStore.getState()
  );

  useEffect(() => {
    return DetectionStore.subscribe(setDetection);
  }, []);

  // Auto-connect to the first active camera if not already processing
  useEffect(() => {
    if (detection.isProcessing || autoConnectAttempted.current || !token) {
      return;
    }
    
    const autoConnect = async () => {
      autoConnectAttempted.current = true;
      try {
        const res = await api.get<any[]>('/api/cameras');
        const activeCamera = res.data.find((c) => c.status === 'active');
        if (activeCamera) {
          console.log(`[Dashboard] Auto-connecting to camera: ${activeCamera.camera_name}`);
          DetectionStore.reset();
          AlertStore.clear();
          wsClient.disconnect();
          wsClient.connect(token, `/ws/camera/${activeCamera.id}`);
        }
      } catch (err) {
        console.error('[Dashboard] Failed to auto-connect to camera:', err);
      }
    };

    autoConnect();
  }, [detection.isProcessing, token]);

  const vW = detection.videoInfo?.width ?? 1280;
  const vH = detection.videoInfo?.height ?? 720;
  const vFPS = detection.videoInfo?.fps ?? 30;

  const handleAnalyzeAnother = () => {
    DetectionStore.reset();
    AlertStore.clear();
    wsClient.disconnect();
    autoConnectAttempted.current = false; // allow auto-connect to try again if needed
    navigate('/upload');
  };

  return (
    <div className="flex-1 flex overflow-hidden p-4 gap-4 relative">
      {/* ── Left: Video feed ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">
        {/* Feed header */}
        <div className="flex items-center justify-between">
          <span className="text-[#9CA3AF] text-xs uppercase tracking-wide font-medium">
            Detection Feed
          </span>
          {detection.videoInfo && (
            <span className="text-[#6B7280] text-xs font-mono">
              {detection.videoInfo.width}×{detection.videoInfo.height} @{' '}
              {detection.videoInfo.fps}fps
            </span>
          )}
        </div>

        {/* Video Canvas — passes idle flag so the watermark shows when no feed is active */}
        <VideoCanvas
          srcWidth={vW}
          srcHeight={vH}
          fps={vFPS}
          idle={!detection.isProcessing && !detection.frameImage}
          active={detection.isProcessing || !!detection.frameImage}
          className="flex-1 rounded border border-[#1F2937]"
        />
      </div>

      {/* ── Right: Alert panel ───────────────────────────────────────── */}
      <div className="w-72 flex flex-col shrink-0">
        <AlertPanel className="flex-1" />
      </div>

      {/* ── Analysis complete banner ──────────────────────────────────── */}
      {detection.isComplete && (
        <div className="absolute bottom-4 left-4 right-[304px] z-30 pointer-events-none">
          <div className="bg-[#121212] border border-[#1F2937] rounded p-3 flex items-center justify-between pointer-events-auto">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 rounded-full bg-[#34C759] shrink-0" />
              <span className="text-white text-xs font-medium">Processing complete</span>
              {detection.videoInfo && (
                <span className="text-[#6B7280] text-xs font-mono">
                  {detection.totalFrames.toLocaleString()} frames ·{' '}
                  {detection.videoInfo.width}×{detection.videoInfo.height} @{' '}
                  {detection.videoInfo.fps}fps
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 ml-4 shrink-0">
              <button
                onClick={handleAnalyzeAnother}
                className="px-3 py-1 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-xs font-medium rounded transition-colors"
              >
                Analyze another →
              </button>
              <button
                onClick={() => DetectionStore.reset()}
                className="px-3 py-1 bg-[#1F2937] hover:bg-[#374151] text-[#9CA3AF] hover:text-white text-xs rounded transition-colors"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
