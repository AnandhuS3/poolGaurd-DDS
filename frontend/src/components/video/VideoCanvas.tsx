/**
 * VideoCanvas.tsx
 * ──────────────────────────────────────────────
 * Renders the analyzed video feed from the backend.
 *
 * ARCHITECTURE:
 * - <img> element displays the raw base64 JPEG frame from the backend.
 *   The backend no longer draws OpenCV annotations; the canvas is the sole drawing layer.
 * - <canvas> overlay draws bounding boxes, labels, and HUD via Canvas API.
 * - requestAnimationFrame (rAF) drives canvas redraws — zero React re-renders per frame.
 * - DetectionStore.latestFrame is read from a ref, not React state.
 * - When idle=true a project-themed watermark is displayed in place of the feed.
 *
 * CONSTRAINT: No DOM elements for bounding boxes. No React state per frame.
 */

import { useRef, useEffect, useCallback } from 'react';
import { DetectionStore } from '../../state/DetectionStore';
import { drawDetections, drawHUD } from './BoundingOverlay';

interface VideoCanvasProps {
  /** Source video dimensions (from video_info message) */
  srcWidth: number;
  srcHeight: number;
  /** Source video fps (from video_info message) – used for duration labels */
  fps?: number;
  className?: string;
  /** When true the feed is inactive – show project watermark instead */
  idle?: boolean;
  /** When false, the canvas overlay is cleared (no bounding boxes drawn) */
  active?: boolean;
}

export function VideoCanvas({ srcWidth, srcHeight, fps = 30, className = '', idle = false, active = true }: VideoCanvasProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);
  // Use a ref so the rAF loop sees the latest value without needing to restart
  const activeRef = useRef(active);
  useEffect(() => { activeRef.current = active; }, [active]);

  // rAF loop – reads from DetectionStore.latestFrame ref, does NOT cause React renders
  const renderLoop = useCallback(() => {
    const cv = canvasRef.current;
    const img = imgRef.current;
    const frame = DetectionStore.latestFrame;

    // When not active, clear the canvas so stale bounding boxes don't persist
    if (!activeRef.current) {
      if (cv) {
        const ctx = cv.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, cv.width, cv.height);
      }
      rafRef.current = requestAnimationFrame(renderLoop);
      return;
    }

    if (cv && img && frame) {
      const rect = img.getBoundingClientRect();
      const dispW = rect.width || cv.clientWidth || 640;
      const dispH = rect.height || cv.clientHeight || 360;

      // Sync canvas dimensions with displayed image size
      if (cv.width !== dispW || cv.height !== dispH) {
        cv.width = dispW;
        cv.height = dispH;
      }

      const ctx = cv.getContext('2d');
      if (ctx) {
        const vW = srcWidth || frame.persons[0]?.bbox[2] || 1280;
        const vH = srcHeight || frame.persons[0]?.bbox[3] || 720;

        drawDetections(ctx, frame.persons, vW, vH, dispW, dispH, fps);
        drawHUD(ctx, frame.frame_number, frame.total_frames, frame.performance.processing_fps);
      }

      // Update the <img> src with the raw JPEG frame from the backend.
      // Backend sends unannotated frames; this canvas is the sole drawing layer.
      if (img.dataset.lastFrame !== frame.frame_number.toString()) {
        img.src = `data:image/jpeg;base64,${frame.analysis_frame}`;
        img.dataset.lastFrame = frame.frame_number.toString();
      }
    }

    rafRef.current = requestAnimationFrame(renderLoop);
  }, [srcWidth, srcHeight, fps]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(renderLoop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [renderLoop]);

  return (
    <div ref={containerRef} className={`relative bg-[#080C14] overflow-hidden ${className}`}>

      {/* ── Watermark layer – visible only when feed is inactive ──────────── */}
      <div
        className="absolute inset-0 flex items-center justify-center transition-opacity duration-300"
        style={{ opacity: idle ? 1 : 0, pointerEvents: 'none' }}
        aria-hidden
      >
        <img
          src="/assets/watermark.svg"
          alt=""
          className="w-full h-full select-none"
          style={{ objectFit: 'contain', maxWidth: '100%', maxHeight: '100%' }}
          draggable={false}
        />
      </div>

      {/* ── Idle text overlay ──────────────────────────────────────────────── */}
      {idle && (
        <div className="absolute inset-0 flex flex-col items-end justify-end pb-8 pr-8 pointer-events-none">
          <p className="text-[#374151] text-[11px] font-mono uppercase tracking-widest select-none">
            No active feed
          </p>
          <p className="text-[#1F2937] text-[10px] font-mono uppercase tracking-widest select-none">
            Upload a video to begin analysis
          </p>
        </div>
      )}

      {/* ── Backend annotated frame ────────────────────────────────────────── */}
      <img
        ref={imgRef}
        alt=""
        className="w-full h-full object-contain block"
        style={{ minHeight: 200, opacity: idle ? 0 : 1 }}
      />

      {/* ── Canvas overlay for bounding box rendering ─────────────────────── */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ mixBlendMode: 'normal' }}
      />
    </div>
  );
}
