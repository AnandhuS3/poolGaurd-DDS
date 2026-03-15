/**
 * Live.tsx
 * Live Camera Feed — real-time CCTV monitoring page.
 *
 * Architecture:
 *   GET /api/cameras → list of registered cameras
 *   GET /api/cameras/{id}/mjpeg?token=<jwt> → MJPEG stream (browsers decode natively via <img>)
 *
 * Features:
 *   - Auto-loads cameras on mount
 *   - 2/3/4 column grid (responsive)
 *   - LIVE / CONNECTING / OFFLINE status badge per tile
 *   - Click tile → fullscreen modal with "Analyze with AI" capability
 *   - Refresh button
 *   - Role-appropriate empty state for guards vs admins
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { parseApiError } from '../services/parseApiError';
import { useAuth } from '../context/AuthContext';
import { wsClient } from '../core/websocket/WebSocketClient';
import { DetectionStore } from '../state/DetectionStore';
import { AlertStore } from '../state/AlertStore';

// ─── Types ────────────────────────────────────────────────────────────────────

interface Camera {
  id: number;
  camera_name: string;
  pool_location: string;
  rtsp_url: string;
  hls_url?: string | null;
  status: 'active' | 'inactive' | 'maintenance';
  assigned_guard_id?: number | null;
  stream_url: string; // relative URL returned by the backend, e.g. "/api/cameras/1/mjpeg"
}

type TileStatus = 'connecting' | 'live' | 'offline';

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Resolve stream URL; append JWT token for MJPEG proxy auth */
function resolveStreamUrl(relativeOrAbsolute: string): string {
  const token = localStorage.getItem('dds_token');
  const base = window.location.origin;
  const url = relativeOrAbsolute.startsWith('http')
    ? relativeOrAbsolute
    : `${base}${relativeOrAbsolute}`;
  if (!token) return url;
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}token=${encodeURIComponent(token)}`;
}

// ─── Camera Tile ──────────────────────────────────────────────────────────────

interface TileProps {
  camera: Camera;
  onExpand: (camera: Camera) => void;
}

function CameraTile({ camera, onExpand }: TileProps) {
  const [tileStatus, setTileStatus] = useState<TileStatus>('connecting');
  const imgRef = useRef<HTMLImageElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const streamUrl = resolveStreamUrl(camera.stream_url);

  // Timeout: if image doesn't load within 10 s, mark offline
  useEffect(() => {
    if (!camera.stream_url || camera.status !== 'active') {
      setTileStatus('offline');
      return;
    }
    setTileStatus('connecting');
    timeoutRef.current = setTimeout(() => {
      setTileStatus((s) => (s === 'connecting' ? 'offline' : s));
    }, 10_000);
    return () => { if (timeoutRef.current) clearTimeout(timeoutRef.current); };
  }, [camera.stream_url, camera.status]);

  return (
    <div
      className="relative bg-[#0D1117] rounded-lg border border-[#1F2937] overflow-hidden cursor-pointer group hover:border-[#374151] transition-colors"
      style={{ aspectRatio: '16/9' }}
      onClick={() => onExpand(camera)}
      title="Click to view details"
    >
      {/* ── Stream image ─────────────────────────────────────────────────── */}
      {camera.status === 'active' && camera.stream_url ? (
        <img
          ref={imgRef}
          src={streamUrl}
          alt={camera.camera_name}
          className="absolute inset-0 w-full h-full object-cover"
          onLoad={() => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            setTileStatus('live');
          }}
          onError={() => {
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
            setTileStatus('offline');
          }}
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center">
          <svg className="w-10 h-10 text-[#374151]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M15 10l4.553-2.277A1 1 0 0121 8.677v6.646a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
            />
          </svg>
        </div>
      )}

      {/* ── Top gradient overlay ─────────────────────────────────────────── */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-transparent to-black/70 pointer-events-none" />

      {/* ── Status badge ─────────────────────────────────────────────────── */}
      <div className="absolute top-2 left-2 flex items-center gap-1.5">
        <StatusBadge status={tileStatus} />
      </div>

      {/* ── Expand icon (on hover, when live) ─────────────────────────────── */}
      {tileStatus === 'live' && (
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="bg-black/50 rounded p-1">
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
              />
            </svg>
          </div>
        </div>
      )}

      {/* ── Bottom label ─────────────────────────────────────────────────── */}
      <div className="absolute bottom-0 left-0 right-0 p-2">
        <p className="text-white text-xs font-semibold truncate">{camera.camera_name}</p>
        <p className="text-[#9CA3AF] text-[10px] truncate">{camera.pool_location}</p>
      </div>

      {/* ── Offline / connecting overlay ─────────────────────────────────── */}
      {tileStatus !== 'live' && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40">
          {tileStatus === 'connecting' ? (
            <div className="flex flex-col items-center gap-2">
              <div className="w-5 h-5 border-2 border-[#3B82F6] border-t-transparent rounded-full animate-spin" />
              <span className="text-[#9CA3AF] text-[10px] font-medium">CONNECTING</span>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <svg className="w-6 h-6 text-[#EF4444]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                />
              </svg>
              <span className="text-[#EF4444] text-[10px] font-semibold uppercase tracking-wider">Offline</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: TileStatus }) {
  if (status === 'live') {
    return (
      <span className="flex items-center gap-1 bg-[#16A34A]/90 text-white text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded">
        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
        LIVE
      </span>
    );
  }
  if (status === 'connecting') {
    return (
      <span className="flex items-center gap-1 bg-[#1D4ED8]/90 text-white text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded">
        CONN…
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 bg-[#991B1B]/90 text-white text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded">
      OFFLINE
    </span>
  );
}

// ─── Fullscreen Modal ─────────────────────────────────────────────────────────

function FullscreenModal({ camera, onClose, onAnalyze }: { camera: Camera; onClose: () => void; onAnalyze: (camera: Camera) => void }) {
  const streamUrl = resolveStreamUrl(camera.stream_url);

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/90 flex flex-col"
      onClick={onClose}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-5 py-3 bg-[#121212] border-b border-[#1F2937] shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        <div>
          <span className="text-white font-semibold text-sm">{camera.camera_name}</span>
          <span className="text-[#6B7280] text-xs ml-3">{camera.pool_location}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-[#34C759] text-xs font-semibold uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-[#34C759] animate-pulse" />
            LIVE
          </span>
          <button
            onClick={onClose}
            className="text-[#9CA3AF] hover:text-white transition-colors p-1"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Stream */}
      <div
        className="flex-1 flex items-center justify-center overflow-hidden p-4 relative bg-black/50"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={streamUrl}
          alt={camera.camera_name}
          className="max-w-full max-h-full object-contain rounded z-10"
          onError={(e) => {
            e.currentTarget.style.display = 'none';
            const fallback = document.createElement('div');
            fallback.className = 'absolute inset-0 flex flex-col items-center justify-center text-[#EF4444] z-0';
            fallback.innerHTML = `
              <svg class="w-12 h-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
              <span class="text-sm font-semibold uppercase tracking-wider">Camera Preview Offline</span>
              <p class="text-[#9CA3AF] text-xs mt-2 text-center max-w-sm font-normal normal-case">
                The visual feed could not be loaded in the browser. You can still click <b>Analyze with AI</b> to process the RTSP stream directly on the backend.
              </p>
            `;
            if (e.currentTarget.parentElement) {
              e.currentTarget.parentElement.appendChild(fallback);
            }
          }}
        />
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between px-5 py-3 bg-[#121212] border-t border-[#1F2937] shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col">
          <span className="text-white text-sm font-medium">Monitoring Active</span>
          <span className="text-[#6B7280] text-xs">Press Esc or click outside to close</span>
        </div>
        
        <button
          onClick={() => onAnalyze(camera)}
          className="flex items-center gap-2 px-6 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-semibold rounded shadow-lg shadow-[#3B82F6]/20 transition-all"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Analyze with AI
        </button>
      </div>
    </div>
  );
}

// ─── Add Camera Modal ─────────────────────────────────────────────────────────

function AddCameraModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    camera_name: '',
    pool_location: 'Main Pool',
    rtsp_url: '',
    status: 'active',
  });

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post('/api/cameras', formData);
      onSuccess();
    } catch (err: unknown) {
      setError(parseApiError(err, 'Failed to register camera'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[#0D1117] border border-[#1F2937] rounded-lg shadow-2xl flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#1F2937] bg-[#121212]">
          <h2 className="text-white font-semibold text-sm uppercase tracking-wide">Register New Camera</h2>
          <button onClick={onClose} className="text-[#9CA3AF] hover:text-white transition-colors">✕</button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-5 flex flex-col gap-4">
          {error && (
            <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/30 text-[#FF3B30] text-xs p-2.5 rounded">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wider">Camera Name</label>
            <input
              type="text"
              required
              className="bg-[#121212] border border-[#1F2937] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="e.g. North Side PTZ"
              value={formData.camera_name}
              onChange={(e) => setFormData({ ...formData, camera_name: e.target.value })}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wider">Pool Location</label>
            <input
              type="text"
              required
              className="bg-[#121212] border border-[#1F2937] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="e.g. Main Pool"
              value={formData.pool_location}
              onChange={(e) => setFormData({ ...formData, pool_location: e.target.value })}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs font-medium uppercase tracking-wider">RTSP/HTTP Stream URL</label>
            <input
              type="url"
              required
              className="bg-[#121212] border border-[#1F2937] rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="rtsp://admin:pass@192.168.1.100/stream"
              value={formData.rtsp_url}
              onChange={(e) => setFormData({ ...formData, rtsp_url: e.target.value })}
            />
            <span className="text-[10px] text-[#6B7280]">Supports RTSP, HTTP, or HTTPS stream URLs.</span>
          </div>

          <div className="flex justify-end gap-3 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] text-white text-sm font-medium rounded transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white text-sm font-semibold rounded transition-colors flex items-center gap-2"
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h5M4 4a9 9 0 100 16" />
                </svg>
              ) : null}
              {loading ? 'Registering...' : 'Register Camera'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function Live() {
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Camera | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [cols, setCols] = useState<2 | 3 | 4>(3);

  const fetchCameras = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Camera[]>('/api/cameras');
      setCameras(res.data);
    } catch (err: unknown) {
      setError('Could not load cameras. Check your connection or contact your administrator.');
      console.error('[Live] fetchCameras error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCameras();
  }, [fetchCameras]);

  const handleAnalyzeLive = (camera: Camera) => {
    if (!token) return;
    
    // Close the modal
    setExpanded(null);

    // Reset detection/alert states for the new session
    DetectionStore.reset();
    AlertStore.clear();

    // Reconnect websocket to the continuous headless stream
    wsClient.disconnect();
    wsClient.connect(token, `/ws/camera/${camera.id}`);

    // Navigate to dashboard immediately
    navigate('/');
  };

  const activeCameras = cameras.filter((c) => c.status === 'active');
  const inactiveCameras = cameras.filter((c) => c.status !== 'active');

  return (
    <div className="flex-1 flex flex-col bg-[#0B0F19] overflow-y-auto">
      {/* ── Page header ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1F2937] shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-white text-sm font-semibold uppercase tracking-wider">Live Camera Feeds</span>
          {!loading && cameras.length > 0 && (
            <span className="text-[#6B7280] text-xs font-mono">
              {activeCameras.length}/{cameras.length} active
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Grid density selector */}
          {cameras.length > 0 && (
            <div className="flex items-center gap-1 bg-[#111827] border border-[#1F2937] rounded p-0.5">
              {([2, 3, 4] as const).map((n) => (
                <button
                  key={n}
                  onClick={() => setCols(n)}
                  className={`px-2 py-0.5 rounded text-xs transition-colors ${
                    cols === n ? 'bg-[#1F2937] text-white' : 'text-[#6B7280] hover:text-white'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          )}

          {/* Add Camera (Admin only) */}
          {user?.role === 'admin' && (
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-1.5 px-3 py-1 bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-xs font-semibold rounded ml-2 shadow-sm transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
              Add Camera
            </button>
          )}

          {/* Refresh */}
          <button
            onClick={fetchCameras}
            disabled={loading}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-[#111827] border border-[#1F2937] hover:border-[#374151] text-[#9CA3AF] hover:text-white text-xs rounded transition-colors disabled:opacity-50"
          >
            <svg
              className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h5M4 4a9 9 0 100 16"
              />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 p-5">

        {/* Error banner */}
        {error && (
          <div className="mb-4 flex items-center gap-3 bg-[#1C1010] border border-[#EF4444]/30 text-[#EF4444] rounded p-3 text-sm">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-[#EF4444]/60 hover:text-[#EF4444] transition-colors"
            >✕</button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
            {Array.from({ length: cols * 2 }).map((_, i) => (
              <div
                key={i}
                className="bg-[#111827] border border-[#1F2937] rounded-lg animate-pulse"
                style={{ aspectRatio: '16/9' }}
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && cameras.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <div className="w-14 h-14 rounded-full bg-[#111827] border border-[#1F2937] flex items-center justify-center">
              <svg className="w-7 h-7 text-[#374151]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M15 10l4.553-2.277A1 1 0 0121 8.677v6.646a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"
                />
              </svg>
            </div>
            <div className="text-center">
              <p className="text-white text-sm font-medium">No cameras registered</p>
              <p className="text-[#6B7280] text-xs mt-1 max-w-xs">
                {user?.role === 'admin'
                  ? 'Head over to the CCTV Manager to register your first hardware camera to begin live AI monitoring.'
                  : 'Contact your administrator to assign cameras to your account.'}
              </p>
            </div>
            {user?.role === 'admin' && (
              <button
                onClick={() => navigate('/admin/cctv-manager')}
                className="mt-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white px-5 py-2 rounded text-xs font-semibold shadow-md shadow-[#3B82F6]/20 transition-all"
              >
                Go to CCTV Manager
              </button>
            )}
          </div>
        )}

        {/* Active camera grid */}
        {!loading && activeCameras.length > 0 && (
          <>
            {inactiveCameras.length > 0 && (
              <p className="text-[#6B7280] text-xs uppercase tracking-wide font-medium mb-3">
                Active — {activeCameras.length} camera{activeCameras.length !== 1 ? 's' : ''}
              </p>
            )}
            <div
              className="grid gap-3"
              style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
            >
              {activeCameras.map((cam) => (
                <CameraTile
                  key={cam.id}
                  camera={cam}
                  onExpand={setExpanded}
                />
              ))}
            </div>
          </>
        )}

        {/* Inactive cameras (condensed list) */}
        {!loading && inactiveCameras.length > 0 && (
          <div className="mt-6">
            <p className="text-[#6B7280] text-xs uppercase tracking-wide font-medium mb-2">
              Inactive / Maintenance — {inactiveCameras.length}
            </p>
            <div className="flex flex-col gap-1">
              {inactiveCameras.map((cam) => (
                <div
                  key={cam.id}
                  className="flex items-center gap-3 bg-[#111827] border border-[#1F2937] rounded px-3 py-2"
                >
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    cam.status === 'maintenance' ? 'bg-[#F59E0B]' : 'bg-[#6B7280]'
                  }`} />
                  <span className="text-[#9CA3AF] text-xs flex-1 truncate">{cam.camera_name}</span>
                  <span className="text-[#6B7280] text-xs truncate">{cam.pool_location}</span>
                  <span className={`text-[10px] font-semibold uppercase tracking-wider ${
                    cam.status === 'maintenance' ? 'text-[#F59E0B]' : 'text-[#6B7280]'
                  }`}>
                    {cam.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Fullscreen modal ────────────────────────────────────────────────── */}
      {expanded && (
        <FullscreenModal camera={expanded} onClose={() => setExpanded(null)} onAnalyze={handleAnalyzeLive} />
      )}

      {/* ── Add Camera Modal ────────────────────────────────────────────────── */}
      {showAddModal && (
        <AddCameraModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            setShowAddModal(false);
            fetchCameras();
          }}
        />
      )}
    </div>
  );
}
