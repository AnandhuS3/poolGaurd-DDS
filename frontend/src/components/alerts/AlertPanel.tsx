/**
 * AlertPanel.tsx
 * List of active warning/danger alerts.
 * Subscribes to AlertStore – updates only on state changes, not per frame.
 */

import { useState, useEffect } from 'react';
import { AlertStore } from '../../state/AlertStore';
import type { ActiveAlert } from '../../types/detection';
import { AlertCard } from './AlertCard';

interface AlertPanelProps {
  className?: string;
}

export function AlertPanel({ className = '' }: AlertPanelProps) {
  const [alerts, setAlerts] = useState<ActiveAlert[]>(() => AlertStore.getAlerts());

  useEffect(() => {
    return AlertStore.subscribe(setAlerts);
  }, []);

  const dangerCount = alerts.filter((a) => a.state === 'danger').length;
  const warningCount = alerts.filter((a) => a.state === 'warning').length;

  return (
    <div
      className={`flex flex-col bg-[#121212] border border-[#1F2937] rounded overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1F2937]">
        <span className="text-white font-semibold text-sm tracking-wide uppercase">
          Active Alerts
        </span>
        <div className="flex items-center gap-2">
          {dangerCount > 0 && (
            <span className="text-xs font-bold bg-[#FF3B30] text-white px-2 py-0.5 rounded">
              {dangerCount} DANGER
            </span>
          )}
          {warningCount > 0 && (
            <span className="text-xs font-bold bg-[#FF9500] text-white px-2 py-0.5 rounded">
              {warningCount} WARN
            </span>
          )}
          {alerts.length === 0 && (
            <span className="text-xs text-[#34C759] font-medium">ALL CLEAR</span>
          )}
        </div>
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[#6B7280] text-sm py-8">
            <div className="w-8 h-8 rounded-full border-2 border-[#34C759] flex items-center justify-center mb-3">
              <span className="text-[#34C759] text-base">✓</span>
            </div>
            <span>No active alerts</span>
            <span className="text-xs text-[#4B5563] mt-1">All tracked persons are safe</span>
          </div>
        ) : (
          alerts.map((alert) => (
            <AlertCard key={`${alert.trackId}-${alert.state}`} alert={alert} />
          ))
        )}
      </div>
    </div>
  );
}
