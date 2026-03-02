/**
 * AlertCard.tsx
 * Single alert entry in the panel.
 */

import type { ActiveAlert } from '../../types/detection';

interface AlertCardProps {
  alert: ActiveAlert;
}

const STATE_CONFIG = {
  danger: {
    border: 'border-[#FF3B30]',
    badge: 'bg-[#FF3B30]',
    icon: '🔴',
    label: 'DANGER',
  },
  warning: {
    border: 'border-[#FF9500]',
    badge: 'bg-[#FF9500]',
    icon: '🟡',
    label: 'WARNING',
  },
  struggling: {
    border: 'border-[#F97316]',
    badge: 'bg-[#F97316]',
    icon: '🟠',
    label: 'STRUGGLING',
  },
} as const;

function timeAgo(epochMs: number): string {
  const sec = Math.floor((Date.now() - epochMs) / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  return `${min}m ${sec % 60}s ago`;
}

export function AlertCard({ alert }: AlertCardProps) {
  const cfg = STATE_CONFIG[alert.state];

  return (
    <div
      className={`rounded border ${cfg.border} bg-[#1A1A1A] p-3 flex flex-col gap-1 text-sm`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold px-2 py-0.5 rounded ${cfg.badge} text-white`}>
            {cfg.label}
          </span>
          <span className="text-[#9CA3AF] font-mono text-xs">ID #{alert.trackId}</span>
        </div>
        <span className="text-[#6B7280] text-xs">{timeAgo(alert.detectedAt)}</span>
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px] mt-1">
        <span className="text-[#9CA3AF]">
          Confidence:{' '}
          <span className="text-white font-medium">
            {(alert.confidence * 100).toFixed(0)}%
          </span>
        </span>
        <span className="text-[#9CA3AF]">
          Duration:{' '}
          <span className="text-white font-medium">
            {(alert.framesUnderwater / 30).toFixed(1)}s
          </span>
        </span>
        {alert.behavior !== 'unknown' && (
          <span className="text-[#9CA3AF] col-span-2">
            Behavior:{' '}
            <span className="text-white font-medium capitalize">{alert.behavior}</span>
          </span>
        )}
      </div>
    </div>
  );
}
