/**
 * Live.tsx
 * Live camera feed page.
 * Future-ready structure for multiple camera streams.
 * Currently shows placeholder with connection status.
 */

import { useWebSocket } from '../core/websocket/useWebSocket';
import { useAuth } from '../context/AuthContext';
import { useEffect } from 'react';
import { wsClient } from '../core/websocket/WebSocketClient';

export function Live() {
  const { status, connect } = useWebSocket();
  const { token } = useAuth();

  useEffect(() => {
    if (token && status === 'idle') {
      connect(token);
    }
  }, [token, status, connect]);

  const isConnected = status === 'connected';

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 gap-6">
      <div className="max-w-md w-full bg-[#121212] border border-[#1F2937] rounded p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-white font-semibold text-sm uppercase tracking-wide">
            Live Feed
          </h2>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded ${
              isConnected
                ? 'bg-[#34C759]/20 text-[#34C759]'
                : 'bg-[#1F2937] text-[#9CA3AF]'
            }`}
          >
            {status.toUpperCase()}
          </span>
        </div>

        <p className="text-[#9CA3AF] text-sm">
          Live RTSP / camera stream support is coming in a future release. This slot is
          reserved for multi-camera input.
        </p>

        {/* Camera slot grid (future expansion) */}
        <div className="grid grid-cols-2 gap-3 mt-2">
          {[1, 2, 3, 4].map((cam) => (
            <div
              key={cam}
              className="aspect-video bg-[#0B0F19] border border-[#1F2937] rounded flex flex-col items-center justify-center text-[#4B5563] text-xs gap-1"
            >
              <span className="text-lg opacity-30">📷</span>
              <span>Camera {cam}</span>
              <span className="text-[10px] text-[#374151]">Not configured</span>
            </div>
          ))}
        </div>

        <div className="text-xs text-[#6B7280] border-t border-[#1F2937] pt-3 mt-1">
          WebSocket status: <span className="text-[#9CA3AF] font-mono">{status}</span>
          {isConnected && (
            <button
              onClick={() => wsClient.disconnect()}
              className="ml-3 text-[#FF3B30] hover:text-red-400 transition-colors"
            >
              Disconnect
            </button>
          )}
          {!isConnected && token && (
            <button
              onClick={() => connect(token)}
              className="ml-3 text-[#3B82F6] hover:text-blue-400 transition-colors"
            >
              Connect
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
