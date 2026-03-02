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
import { VideoCanvas } from '../components/video/VideoCanvas';
import { AlertPanel } from '../components/alerts/AlertPanel';
import { DetectionStore, type DetectionState } from '../state/DetectionStore';

export function Dashboard() {
  const [detection, setDetection] = useState<DetectionState>(() =>
    DetectionStore.getState()
  );

  useEffect(() => {
    return DetectionStore.subscribe(setDetection);
  }, []);

  const vW = detection.videoInfo?.width ?? 1280;
  const vH = detection.videoInfo?.height ?? 720;
  const vFPS = detection.videoInfo?.fps ?? 30;

  return (
    <div className="flex-1 flex overflow-hidden p-4 gap-4">
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

        {/* Video Canvas */}
        <VideoCanvas
          srcWidth={vW}
          srcHeight={vH}
          fps={vFPS}
          className="flex-1 rounded border border-[#1F2937]"
        />

        {/* Empty state */}
        {!detection.isProcessing && !detection.frameImage && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center text-[#6B7280]">
              <div className="text-4xl mb-3 opacity-30">📹</div>
              <p className="text-sm">No active feed</p>
              <p className="text-xs text-[#4B5563] mt-1">
                Upload a video to begin analysis
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Right: Alert panel ───────────────────────────────────────── */}
      <div className="w-72 flex flex-col shrink-0">
        <AlertPanel className="flex-1" />
      </div>
    </div>
  );
}
