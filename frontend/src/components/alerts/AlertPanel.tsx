/**
 * AlertPanel.tsx
 * Vertically split panel: Active Alerts (top 50%) / Acknowledged Alerts (bottom 50%).
 * Subscribes to AlertStore – updates only on state changes, not per frame.
 */

import { useState, useEffect } from 'react';
import { AlertStore } from '../../state/AlertStore';
import type { ActiveAlert, AcknowledgedAlert } from '../../types/detection';
import { AlertCard } from './AlertCard';

interface AlertPanelProps {
  className?: string;
}

function formatTime(epochMs: number): string {
  return new Date(epochMs).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function timeAgo(epochMs: number): string {
  const sec = Math.floor((Date.now() - epochMs) / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  return `${min}m ${sec % 60}s ago`;
}

const ACK_STATE_COLORS: Record<string, string> = {
  danger: 'text-[#FF3B30]',
  struggling: 'text-[#F97316]',
  warning: 'text-[#FF9500]',
};

function AcknowledgedCard({ alert }: { alert: AcknowledgedAlert }) {
  const stateColor = ACK_STATE_COLORS[alert.state] ?? 'text-[#9CA3AF]';
  return (
    <div className="rounded border border-[#1F2937] bg-[#111111] px-3 py-2 flex flex-col gap-1 text-[11px]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`font-bold uppercase ${stateColor}`}>{alert.state}</span>
          <span className="text-[#6B7280] font-mono">ID #{alert.trackId}</span>
        </div>
        <span className="text-[#34C759] text-[10px] font-medium">✓ ACK</span>
      </div>
      <div className="flex items-center justify-between text-[#4B5563]">
        <span>Detected: <span className="text-[#6B7280]">{formatTime(alert.detectedAt)}</span></span>
        <span>Acked: <span className="text-[#6B7280]">{timeAgo(alert.acknowledgedAt)}</span></span>
      </div>
      <div className="flex items-center gap-4 text-[#4B5563]">
        <span>Confidence: <span className="text-[#6B7280]">{(alert.confidence * 100).toFixed(0)}%</span></span>
        <span>Duration: <span className="text-[#6B7280]">{(alert.framesUnderwater / 30).toFixed(1)}s</span></span>
      </div>
    </div>
  );
}

export function AlertPanel({ className = '' }: AlertPanelProps) {
  const [alerts, setAlerts] = useState<ActiveAlert[]>(() => AlertStore.getAlerts());
  const [acknowledged, setAcknowledged] = useState<AcknowledgedAlert[]>(() => AlertStore.getAcknowledgedAlerts());

  useEffect(() => {
    const unsubActive = AlertStore.subscribe(setAlerts);
    const unsubAck = AlertStore.subscribeAcknowledged(setAcknowledged);
    return () => {
      unsubActive();
      unsubAck();
    };
  }, []);

  const dangerCount = alerts.filter((a) => a.state === 'danger').length;
  const strugglingCount = alerts.filter((a) => a.state === 'struggling').length;
  const warningCount = alerts.filter((a) => a.state === 'warning').length;

  return (
    <div
      className={`flex flex-col bg-[#121212] border border-[#1F2937] rounded overflow-hidden ${className}`}
    >
      {/* ── Top half: Active Alerts ──────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-h-0 border-b border-[#1F2937]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1F2937] shrink-0">
          <span className="text-white font-semibold text-sm tracking-wide uppercase">
            Active Alerts
          </span>
          <div className="flex items-center gap-2">
            {dangerCount > 0 && (
              <span className="text-xs font-bold bg-[#FF3B30] text-white px-2 py-0.5 rounded">
                {dangerCount} DANGER
              </span>
            )}
            {strugglingCount > 0 && (
              <span className="text-xs font-bold bg-[#F97316] text-white px-2 py-0.5 rounded">
                {strugglingCount} STRUGGLING
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
            {alerts.length > 0 && (
              <button
                onClick={() => AlertStore.silenceAlarm()}
                title="Silence alarm"
                className="text-[#6B7280] hover:text-white transition-colors ml-1"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.143 17.082a24.248 24.248 0 0 0 3.844.148m-3.844-.148a23.856 23.856 0 0 1-5.455-1.31 8.964 8.964 0 0 0 2.3-5.542m3.155 6.852a3 3 0 0 0 5.667 1.069m1.714-8.996a9 9 0 0 0-3.838-5.085M10.5 3.375a9 9 0 0 1 3 0m0 0a9 9 0 0 1 6.738 10.184M13.5 3.375A9.003 9.003 0 0 0 3.32 13.559M3 3l18 18" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Active alert list */}
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
              <AlertCard
                key={`${alert.trackId}-${alert.state}`}
                alert={alert}
                onDismiss={() => AlertStore.dismiss(alert.trackId)}
              />
            ))
          )}
        </div>
      </div>

      {/* ── Bottom half: Acknowledged Alerts ─────────────────────────────── */}
      <div className="flex flex-col flex-1 min-h-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1F2937] shrink-0">
          <span className="text-[#9CA3AF] font-semibold text-sm tracking-wide uppercase">
            Acknowledged
          </span>
          {acknowledged.length > 0 && (
            <span className="text-xs text-[#6B7280] font-mono">{acknowledged.length}</span>
          )}
        </div>

        {/* Acknowledged alert list */}
        <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
          {acknowledged.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-[#4B5563] text-xs py-6">
              <span>No acknowledged alerts</span>
            </div>
          ) : (
            acknowledged.map((alert) => (
              <AcknowledgedCard key={`ack-${alert.trackId}-${alert.acknowledgedAt}`} alert={alert} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

