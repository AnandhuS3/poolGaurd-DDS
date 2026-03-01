/**
 * StatusBar.tsx
 * Bottom status bar showing real-time processing metrics.
 */

import { useState, useEffect } from 'react';
import { DetectionStore, type DetectionState } from '../../state/DetectionStore';

export function StatusBar() {
  const [state, setState] = useState<DetectionState>(() => DetectionStore.getState());

  useEffect(() => {
    return DetectionStore.subscribe(setState);
  }, []);

  const progress =
    state.totalFrames > 0
      ? Math.round((state.frameNumber / state.totalFrames) * 100)
      : 0;

  const perf = state.performance;

  return (
    <footer className="h-8 flex items-center justify-between px-5 bg-[#0D1117] border-t border-[#1F2937] shrink-0 text-[11px] text-[#6B7280] z-20">
      {/* Left: Status */}
      <div className="flex items-center gap-3">
        {state.isProcessing && (
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF9500] animate-pulse" />
            Processing
          </span>
        )}
        {state.isComplete && (
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#34C759]" />
            Complete
          </span>
        )}
        {!state.isProcessing && !state.isComplete && (
          <span className="text-[#4B5563]">Idle</span>
        )}

        {state.error && (
          <span className="text-[#FF3B30]">Error: {state.error}</span>
        )}
      </div>

      {/* Center: Progress */}
      {state.isProcessing && (
        <div className="flex items-center gap-2">
          <div className="w-32 h-1 bg-[#1F2937] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3B82F6] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span>
            {state.frameNumber}/{state.totalFrames} ({progress}%)
          </span>
        </div>
      )}

      {/* Right: Performance */}
      <div className="flex items-center gap-4">
        {perf && (
          <>
            <span>
              Processing FPS:{' '}
              <span className={perf.real_time ? 'text-[#34C759]' : 'text-[#FF9500]'}>
                {perf.processing_fps.toFixed(1)}
              </span>
            </span>
            <span>
              Speed: <span className="text-[#9CA3AF]">{perf.speed_ratio.toFixed(2)}×</span>
            </span>
            <span>
              Skip: <span className="text-[#9CA3AF]">{perf.frame_skip}</span>
            </span>
          </>
        )}
        {state.summary && (
          <span>
            Tracked:{' '}
            <span className="text-white">{state.summary.total}</span>{' '}
            <span className="text-[#FF3B30]">
              {state.summary.danger > 0 ? `${state.summary.danger}D` : ''}
            </span>
            {' '}
            <span className="text-[#FF9500]">
              {state.summary.warning > 0 ? `${state.summary.warning}W` : ''}
            </span>
          </span>
        )}
      </div>
    </footer>
  );
}
