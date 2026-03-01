/**
 * VideoCanvas.tsx
 * ──────────────────────────────────────────────
 * Renders the analyzed video feed from the backend.
 *
 * ARCHITECTURE:
 * - <img> element displays the base64 JPEG annotated frame from backend.
 * - <canvas> overlay draws clean bounding boxes via Canvas API.
 * - requestAnimationFrame (rAF) drives canvas redraws — zero React re-renders per frame.
 * - DetectionStore.latestFrame is read from a ref, not React state.
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
  className?: string;
}

export function VideoCanvas({ srcWidth, srcHeight, className = '' }: VideoCanvasProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // rAF loop – reads from DetectionStore.latestFrame ref, does NOT cause React renders
  const renderLoop = useCallback(() => {
    const cv = canvasRef.current;
    const img = imgRef.current;
    const frame = DetectionStore.latestFrame;

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

        drawDetections(ctx, frame.persons, vW, vH, dispW, dispH);
        drawHUD(ctx, frame.frame_number, frame.total_frames, frame.performance.processing_fps);
      }

      // Update the <img> src from base64 analysis frame (annotated by backend too)
      // We use the backend frame as the video source; our canvas adds clean overlays on top.
      if (img.dataset.lastFrame !== frame.frame_number.toString()) {
        img.src = `data:image/jpeg;base64,${frame.analysis_frame}`;
        img.dataset.lastFrame = frame.frame_number.toString();
      }
    }

    rafRef.current = requestAnimationFrame(renderLoop);
  }, [srcWidth, srcHeight]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(renderLoop);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [renderLoop]);

  return (
    <div ref={containerRef} className={`relative bg-black overflow-hidden ${className}`}>
      {/* Backend annotated frame */}
      <img
        ref={imgRef}
        alt="Detection feed"
        className="w-full h-full object-contain block"
        style={{ minHeight: 200 }}
      />
      {/* Canvas overlay for additional clean bounding box rendering */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{ mixBlendMode: 'normal' }}
      />
    </div>
  );
}
