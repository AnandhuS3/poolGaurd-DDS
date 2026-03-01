/**
 * BoundingOverlay.ts
 * ──────────────────────────────────────────────
 * Pure Canvas API drawing utilities.
 * NO React. NO DOM elements for bounding boxes.
 * Called inside requestAnimationFrame loop.
 */

import type { Person } from '../../types/detection';

// Color mapping per detection state
const STATE_COLORS: Record<string, string> = {
  safe: '#34C759',
  warning: '#FF9500',
  danger: '#FF3B30',
  attention: '#FF9500',
};

const FONT = '11px Inter, monospace';
const LABEL_PADDING = 4;
const BOX_LINE_WIDTH = 2;

/**
 * Draw all bounding boxes + labels onto the canvas.
 * Canvas is sized to match the displayed image dimensions.
 */
export function drawDetections(
  ctx: CanvasRenderingContext2D,
  persons: Person[],
  srcWidth: number,
  srcHeight: number,
  canvasWidth: number,
  canvasHeight: number
): void {
  ctx.clearRect(0, 0, canvasWidth, canvasHeight);

  if (persons.length === 0) return;

  // Scale factors – backend bbox is in original video pixel coords
  const scaleX = canvasWidth / srcWidth;
  const scaleY = canvasHeight / srcHeight;

  ctx.font = FONT;
  ctx.lineWidth = BOX_LINE_WIDTH;

  for (const person of persons) {
    const [x1, y1, x2, y2] = person.bbox;

    const sx1 = Math.round(x1 * scaleX);
    const sy1 = Math.round(y1 * scaleY);
    const sw = Math.round((x2 - x1) * scaleX);
    const sh = Math.round((y2 - y1) * scaleY);

    const color = STATE_COLORS[person.status] ?? STATE_COLORS.safe;

    // Bounding box
    ctx.strokeStyle = color;
    ctx.strokeRect(sx1, sy1, sw, sh);

    // Fill with very low alpha for visual depth
    ctx.fillStyle = `${color}18`;
    ctx.fillRect(sx1, sy1, sw, sh);

    // Label
    const durationSec = (person.frames_underwater / 30).toFixed(1);
    const label = `#${person.id}  ${person.state}  ${(person.confidence * 100).toFixed(0)}%  ${durationSec}s`;

    const metrics = ctx.measureText(label);
    const labelW = metrics.width + LABEL_PADDING * 2;
    const labelH = 16;
    const labelY = sy1 > labelH + 2 ? sy1 - labelH - 2 : sy1 + sh + 2;

    // Label background
    ctx.fillStyle = color;
    ctx.fillRect(sx1, labelY, labelW, labelH);

    // Label text
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(label, sx1 + LABEL_PADDING, labelY + labelH - LABEL_PADDING);
  }
}

/**
 * Draw a minimal HUD in the top-left corner with frame stats.
 */
export function drawHUD(
  ctx: CanvasRenderingContext2D,
  frameNumber: number,
  totalFrames: number,
  fps: number
): void {
  const text = `Frame ${frameNumber}/${totalFrames}  •  ${fps.toFixed(1)} fps`;
  ctx.font = '10px Inter, monospace';
  ctx.fillStyle = 'rgba(0,0,0,0.55)';
  ctx.fillRect(6, 6, ctx.measureText(text).width + 10, 18);
  ctx.fillStyle = '#FFFFFF';
  ctx.fillText(text, 11, 19);
}
