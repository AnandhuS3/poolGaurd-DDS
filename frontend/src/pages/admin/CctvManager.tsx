/**
 * CctvManager.tsx
 * Admin-only page for registering and managing CCTV cameras.
 * Includes guard assignment — controls which cameras appear on each guard's mobile app.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { parseApiError } from '../../services/parseApiError';

interface Guard {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface Camera {
  id: number;
  camera_name: string;
  pool_location: string;
  rtsp_url: string;
  hls_url?: string | null;
  status: 'active' | 'inactive' | 'maintenance';
  assigned_guard_id?: number | null;
  stream_url?: string;
}

type EditFormData = {
  camera_name: string;
  pool_location: string;
  rtsp_url: string;
  hls_url: string;
  status: 'active' | 'inactive' | 'maintenance';
  assigned_guard_id: number | null;
};

export function CctvManager() {
  const navigate = useNavigate();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guards, setGuards] = useState<Guard[]>([]);

  // ── Add form ──────────────────────────────────────────────────
  const [showAddForm, setShowAddForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    camera_name: '',
    pool_location: '',
    rtsp_url: '',
    status: 'active' as const,
  });

  // ── Edit modal ────────────────────────────────────────────────
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [editForm, setEditForm] = useState<EditFormData>({
    camera_name: '',
    pool_location: '',
    rtsp_url: '',
    hls_url: '',
    status: 'active',
    assigned_guard_id: null,
  });
  const [editSaving, setEditSaving] = useState(false);

  // ─────────────────────────────────────────────────────────────

  const fetchCameras = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get<Camera[]>('/api/cameras');
      setCameras(res.data);
      setError(null);
    } catch (err) {
      setError('Failed to load cameras.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch guard list for assignment dropdown
  const fetchGuards = useCallback(async () => {
    try {
      const res = await api.get<Guard[]>('/api/admin/users');
      setGuards((res.data ?? []).filter((u) => u.role === 'guard' && u.is_active));
    } catch {
      // non-critical — silently ignore
    }
  }, []);

  useEffect(() => {
    fetchCameras();
    fetchGuards();
  }, [fetchCameras, fetchGuards]);

  // ── Add ───────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post('/api/cameras', formData);
      navigate('/live');
    } catch (err) {
      alert(parseApiError(err, 'Failed to add camera'));
      setIsSubmitting(false);
    }
  };

  // ── Delete ────────────────────────────────────────────────────
  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to completely remove this camera and stop its continuous analysis?')) return;
    try {
      await api.delete(`/api/cameras/${id}`);
      fetchCameras();
    } catch (err) {
      alert(parseApiError(err, 'Failed to delete camera'));
    }
  };

  // ── Pause / Resume toggle ─────────────────────────────────────
  const toggleStatus = async (camera: Camera) => {
    const newStatus = camera.status === 'active' ? 'maintenance' : 'active';
    try {
      await api.patch(`/api/cameras/${camera.id}`, { status: newStatus });
      fetchCameras();
    } catch (err) {
      alert(parseApiError(err, 'Failed to update status'));
    }
  };

  // ── Open edit modal ───────────────────────────────────────────
  const openEdit = (camera: Camera) => {
    setEditingCamera(camera);
    setEditForm({
      camera_name: camera.camera_name,
      pool_location: camera.pool_location,
      rtsp_url: camera.rtsp_url,
      hls_url: camera.hls_url ?? '',
      status: camera.status,
      assigned_guard_id: camera.assigned_guard_id ?? null,
    });
  };

  // ── Save edit ─────────────────────────────────────────────────
  const handleEditSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCamera) return;
    setEditSaving(true);
    try {
      const payload: Record<string, unknown> = {
        camera_name: editForm.camera_name,
        pool_location: editForm.pool_location,
        rtsp_url: editForm.rtsp_url,
        status: editForm.status,
        // null = unassign (all guards see it); number = specific guard only
        assigned_guard_id: editForm.assigned_guard_id,
      };
      if (editForm.hls_url.trim()) payload.hls_url = editForm.hls_url.trim();
      await api.patch(`/api/cameras/${editingCamera.id}`, payload);
      setEditingCamera(null);
      fetchCameras();
    } catch (err) {
      alert(parseApiError(err, 'Failed to update camera'));
    } finally {
      setEditSaving(false);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // Status badge helper
  const statusBadge = (status: Camera['status']) => {
    const styles: Record<Camera['status'], string> = {
      active:      'bg-[#10B981]/20 text-[#10B981]',
      inactive:    'bg-[#6B7280]/20 text-[#9CA3AF]',
      maintenance: 'bg-[#EF4444]/20 text-[#EF4444]',
    };
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${styles[status]}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="flex-1 p-6 flex flex-col gap-6 overflow-y-auto">
      {/* ── Header ── */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-white">CCTV Manager</h2>
          <p className="text-sm text-[#9CA3AF] mt-1">
            Register and configure hardware cameras. Active cameras are automatically monitored by the AI analysis engine.
          </p>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-[#3B82F6] hover:bg-[#2563EB] text-white px-4 py-2 rounded text-sm font-semibold transition-colors"
        >
          {showAddForm ? 'Cancel' : '+ Register Camera'}
        </button>
      </div>

      {/* ── Add Form ── */}
      {showAddForm && (
        <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-5">
          <h3 className="text-white font-medium mb-4 uppercase text-xs tracking-wider">New Camera Setup</h3>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#9CA3AF] uppercase">Camera Name</label>
                <input
                  type="text"
                  required
                  className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2"
                  placeholder="e.g. Deep End PTZ"
                  value={formData.camera_name}
                  onChange={(e) => setFormData({ ...formData, camera_name: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#9CA3AF] uppercase">Pool Location</label>
                <input
                  type="text"
                  required
                  className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2"
                  placeholder="e.g. Main Pool"
                  value={formData.pool_location}
                  onChange={(e) => setFormData({ ...formData, pool_location: e.target.value })}
                />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-[#9CA3AF] uppercase">RTSP/HTTP Stream URL (Hardware Connection)</label>
              <input
                type="url"
                required
                className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2"
                placeholder="rtsp://user:pass@192.168.1.50:554/stream"
                value={formData.rtsp_url}
                onChange={(e) => setFormData({ ...formData, rtsp_url: e.target.value })}
              />
            </div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 self-start bg-[#10B981] hover:bg-[#059669] disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded text-sm font-semibold transition-colors"
            >
              {isSubmitting ? 'Saving...' : 'Save & Start Analysis'}
            </button>
          </form>
        </div>
      )}

      {/* ── Camera Table ── */}
      {error ? (
        <div className="text-red-500">{error}</div>
      ) : loading ? (
        <div className="text-white">Loading cameras...</div>
      ) : (
        <div className="bg-[#111827] border border-[#1F2937] rounded-lg overflow-hidden">
          <table className="w-full text-left text-sm text-[#9CA3AF]">
            <thead className="text-xs uppercase bg-[#1F2937] text-white">
              <tr>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Location</th>
                <th className="px-5 py-3">Stream URL</th>
                <th className="px-5 py-3">Status / AI Engine</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {cameras.map((c) => (
                <tr key={c.id} className="hover:bg-[#1A2234] transition-colors">
                  <td className="px-5 py-3 font-medium text-white">{c.camera_name}</td>
                  <td className="px-5 py-3">{c.pool_location}</td>
                  <td className="px-5 py-3 font-mono text-xs max-w-[200px] truncate" title={c.rtsp_url}>
                    {c.rtsp_url}
                  </td>
                  <td className="px-5 py-3">{statusBadge(c.status)}</td>
                  <td className="px-5 py-3 text-right space-x-3">
                    {/* Edit */}
                    <button
                      id={`edit-camera-${c.id}`}
                      onClick={() => openEdit(c)}
                      className="text-xs text-[#F59E0B] hover:text-[#D97706] font-medium"
                    >
                      Edit
                    </button>
                    {/* Pause / Resume */}
                    <button
                      id={`toggle-camera-${c.id}`}
                      onClick={() => toggleStatus(c)}
                      className="text-xs text-[#3B82F6] hover:text-[#2563EB]"
                    >
                      {c.status === 'active' ? 'Pause' : 'Resume'}
                    </button>
                    {/* Delete */}
                    <button
                      id={`delete-camera-${c.id}`}
                      onClick={() => handleDelete(c.id)}
                      className="text-xs text-[#EF4444] hover:text-[#DC2626]"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {cameras.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-sm">
                    No cameras registered yet. Add a camera to begin real-time connection.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Edit Modal ── */}
      {editingCamera && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={(e) => { if (e.target === e.currentTarget) setEditingCamera(null); }}
        >
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 w-full max-w-lg shadow-2xl">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-white font-semibold text-base">
                Edit Camera — <span className="text-[#9CA3AF] font-normal">ID #{editingCamera.id}</span>
              </h3>
              <button
                onClick={() => setEditingCamera(null)}
                className="text-[#6B7280] hover:text-white text-xl leading-none"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEditSave} className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-[#9CA3AF] uppercase">Camera Name</label>
                  <input
                    id="edit-camera-name"
                    type="text"
                    required
                    className="bg-[#0B0F19] border border-[#1F2937] focus:border-[#3B82F6] outline-none text-white text-sm rounded px-3 py-2 transition-colors"
                    value={editForm.camera_name}
                    onChange={(e) => setEditForm({ ...editForm, camera_name: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs text-[#9CA3AF] uppercase">Pool Location</label>
                  <input
                    id="edit-pool-location"
                    type="text"
                    required
                    className="bg-[#0B0F19] border border-[#1F2937] focus:border-[#3B82F6] outline-none text-white text-sm rounded px-3 py-2 transition-colors"
                    value={editForm.pool_location}
                    onChange={(e) => setEditForm({ ...editForm, pool_location: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#9CA3AF] uppercase">RTSP / HTTP Stream URL</label>
                <input
                  id="edit-rtsp-url"
                  type="url"
                  required
                  className="bg-[#0B0F19] border border-[#1F2937] focus:border-[#3B82F6] outline-none text-white text-sm rounded px-3 py-2 font-mono transition-colors"
                  placeholder="rtsp://user:pass@192.168.1.50:554/stream"
                  value={editForm.rtsp_url}
                  onChange={(e) => setEditForm({ ...editForm, rtsp_url: e.target.value })}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#9CA3AF] uppercase">
                  HLS URL <span className="normal-case text-[#6B7280]">(optional — leave blank if not used)</span>
                </label>
                <input
                  id="edit-hls-url"
                  type="url"
                  className="bg-[#0B0F19] border border-[#1F2937] focus:border-[#3B82F6] outline-none text-white text-sm rounded px-3 py-2 font-mono transition-colors"
                  placeholder="http://your-streaming-server/stream.m3u8"
                  value={editForm.hls_url}
                  onChange={(e) => setEditForm({ ...editForm, hls_url: e.target.value })}
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#9CA3AF] uppercase">Status</label>
                <select
                  id="edit-status"
                  className="bg-[#0B0F19] border border-[#1F2937] focus:border-[#3B82F6] outline-none text-white text-sm rounded px-3 py-2 transition-colors"
                  value={editForm.status}
                  onChange={(e) => setEditForm({ ...editForm, status: e.target.value as EditFormData['status'] })}
                >
                  <option value="active">Active — AI analysis running</option>
                  <option value="inactive">Inactive — camera disabled</option>
                  <option value="maintenance">Maintenance — temporarily paused</option>
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs text-[#9CA3AF] uppercase">
                  Assign to Guard{' '}
                  <span className="normal-case text-[#6B7280]">
                    (controls mobile app visibility)
                  </span>
                </label>
                <select
                  id="edit-assigned-guard"
                  className="bg-[#0B0F19] border border-[#1F2937] focus:border-[#3B82F6] outline-none text-white text-sm rounded px-3 py-2 transition-colors"
                  value={editForm.assigned_guard_id ?? ''}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      assigned_guard_id: e.target.value === '' ? null : Number(e.target.value),
                    })
                  }
                >
                  <option value="">All guards (no restriction)</option>
                  {guards.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name} — {g.email}
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-[#4B5563]">
                  If assigned: only that guard sees this camera in the mobile app. Leave blank to show to all guards.
                </p>
              </div>


              <div className="flex justify-end gap-3 mt-2">
                <button
                  type="button"
                  onClick={() => setEditingCamera(null)}
                  className="px-4 py-2 rounded text-sm text-[#9CA3AF] hover:text-white border border-[#1F2937] hover:border-[#374151] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSaving}
                  id="edit-camera-save"
                  className="px-6 py-2 rounded text-sm font-semibold bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white transition-colors"
                >
                  {editSaving ? 'Saving…' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
