/**
 * GuardMonitor.tsx
 * Admin-only page: Mobile app and guard activity overview.
 * Shows which guards are online, which cameras they can see, and recent alert activity.
 */

import { useEffect, useState, useCallback } from 'react';
import api from '../../services/api';

interface Guard {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  phone_number?: string;
}

interface Camera {
  id: number;
  camera_name: string;
  pool_location: string;
  status: 'active' | 'inactive' | 'maintenance';
  assigned_guard_id: number | null;
}

interface Session {
  id?: number;
  name: string;
  email: string;
  role: string;
  login_time: string;
  ip_address?: string;
}

interface AlertRecord {
  id: number;
  alert_type?: string;
  camera_name?: string;
  triggered_at?: string;
  resolved_at?: string | null;
}

export function GuardMonitor() {
  const [guards, setGuards] = useState<Guard[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const [guardsRes, camerasRes, sessionsRes, alertsRes] = await Promise.all([
        api.get<Guard[]>('/api/admin/users').catch(() => ({ data: [] })),
        api.get<Camera[]>('/api/cameras').catch(() => ({ data: [] })),
        api.get<Session[]>('/api/admin/sessions').catch(() => ({ data: [] })),
        api.get<AlertRecord[]>('/api/admin/alerts?limit=50').catch(() => ({ data: [] })),
      ]);
      setGuards((guardsRes.data ?? []).filter((u) => u.role === 'guard'));
      setCameras(camerasRes.data ?? []);
      setSessions(sessionsRes.data ?? []);
      setAlerts(alertsRes.data ?? []);
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 30_000);
    return () => clearInterval(id);
  }, [fetchAll]);

  const isGuardOnline = (email: string) =>
    sessions.some((s) => s.email === email && s.role === 'guard');

  const getSessionForGuard = (email: string) =>
    sessions.find((s) => s.email === email);

  /** Cameras that guard can see: assigned to them OR unassigned */
  const camerasForGuard = (guardId: number) =>
    cameras.filter(
      (c) => c.assigned_guard_id === null || c.assigned_guard_id === guardId
    );

  const recentAlerts = alerts.slice(0, 10);
  const openAlerts = alerts.filter((a) => !a.resolved_at);

  return (
    <div className="p-6 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-white font-semibold text-base">📱 Guard Monitor</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">
            Real-time overview of guard mobile app activity and camera assignments.
            {lastUpdated && (
              <span className="ml-2 text-[#4B5563]">
                Updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>
        <button
          onClick={fetchAll}
          disabled={loading}
          className="px-3 py-1.5 bg-[#1F2937] hover:bg-[#374151] disabled:opacity-50 text-[#9CA3AF] hover:text-white text-xs rounded transition-colors"
        >
          {loading ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-4">
        {[
          {
            label: 'Guards Online',
            value: sessions.filter((s) => s.role === 'guard').length,
            total: guards.length,
            color: 'text-[#10B981]',
          },
          {
            label: 'Active Cameras',
            value: cameras.filter((c) => c.status === 'active').length,
            total: cameras.length,
            color: 'text-[#3B82F6]',
          },
          {
            label: 'Open Alerts',
            value: openAlerts.length,
            total: alerts.length,
            color: openAlerts.length > 0 ? 'text-[#EF4444]' : 'text-[#10B981]',
          },
          {
            label: 'Unassigned Cameras',
            value: cameras.filter((c) => c.assigned_guard_id === null).length,
            total: cameras.length,
            color: 'text-[#F59E0B]',
          },
        ].map(({ label, value, total, color }) => (
          <div key={label} className="bg-[#121212] border border-[#1F2937] rounded p-4">
            <p className="text-[#6B7280] text-xs uppercase tracking-wide">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${color}`}>
              {value}
              <span className="text-[#4B5563] text-sm font-normal"> / {total}</span>
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Guard cards */}
        <div className="flex flex-col gap-3">
          <h2 className="text-white text-sm font-semibold uppercase tracking-wide">
            Guards &amp; Camera Access
          </h2>
          {loading && guards.length === 0 ? (
            <div className="text-[#9CA3AF] text-sm">Loading…</div>
          ) : guards.length === 0 ? (
            <div className="bg-[#121212] border border-[#1F2937] rounded p-6 text-center text-[#6B7280] text-sm">
              No guards registered yet.
            </div>
          ) : (
            guards.map((g) => {
              const online = isGuardOnline(g.email);
              const session = getSessionForGuard(g.email);
              const visibleCameras = camerasForGuard(g.id);
              const activeCams = visibleCameras.filter((c) => c.status === 'active');

              return (
                <div
                  key={g.id}
                  className={`bg-[#121212] border rounded p-4 flex flex-col gap-3 ${
                    online ? 'border-[#10B981]/40' : 'border-[#1F2937]'
                  }`}
                >
                  {/* Guard header */}
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            online ? 'bg-[#10B981]' : 'bg-[#4B5563]'
                          }`}
                        />
                        <span className="text-white font-medium text-sm">{g.name}</span>
                        {!g.is_active && (
                          <span className="px-1.5 py-0.5 bg-[#EF4444]/10 text-[#EF4444] text-[10px] rounded">
                            DEACTIVATED
                          </span>
                        )}
                      </div>
                      <p className="text-[#6B7280] text-xs mt-0.5">{g.email}</p>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        online
                          ? 'bg-[#10B981]/10 text-[#10B981]'
                          : 'bg-[#1F2937] text-[#6B7280]'
                      }`}
                    >
                      {online ? '● Online' : '○ Offline'}
                    </span>
                  </div>

                  {/* Session info */}
                  {session && (
                    <div className="text-[10px] text-[#9CA3AF] bg-[#0B0F19] rounded px-3 py-2 flex gap-4">
                      <span>
                        Logged in:{' '}
                        <strong className="text-white">
                          {new Date(session.login_time).toLocaleTimeString()}
                        </strong>
                      </span>
                      {session.ip_address && (
                        <span>
                          IP: <strong className="text-white font-mono">{session.ip_address}</strong>
                        </span>
                      )}
                    </div>
                  )}

                  {/* Camera access */}
                  <div>
                    <p className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-1.5">
                      Mobile Camera Access ({activeCams.length} active / {visibleCameras.length} total)
                    </p>
                    {visibleCameras.length === 0 ? (
                      <p className="text-[#4B5563] text-xs italic">No cameras visible to this guard.</p>
                    ) : (
                      <div className="flex flex-wrap gap-1.5">
                        {visibleCameras.map((c) => (
                          <span
                            key={c.id}
                            className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                              c.status === 'active'
                                ? 'bg-[#10B981]/10 text-[#10B981]'
                                : 'bg-[#1F2937] text-[#6B7280]'
                            }`}
                            title={`${c.pool_location} — ${c.status}${c.assigned_guard_id === null ? ' (shared)' : ' (assigned)'}`}
                          >
                            {c.camera_name}
                            {c.assigned_guard_id === null && (
                              <span className="opacity-60 ml-1">(all)</span>
                            )}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Recent alert activity */}
        <div className="flex flex-col gap-3">
          <h2 className="text-white text-sm font-semibold uppercase tracking-wide">
            Recent Alert Activity
          </h2>
          <div className="bg-[#121212] border border-[#1F2937] rounded overflow-hidden">
            {recentAlerts.length === 0 ? (
              <div className="p-6 text-center text-[#6B7280] text-sm">No alerts recorded yet.</div>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#1F2937]">
                    {['#', 'Type', 'Camera', 'Time', 'Status'].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-2.5 text-left text-[#9CA3AF] uppercase tracking-wide"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recentAlerts.map((a) => {
                    const isOpen = !a.resolved_at;
                    return (
                      <tr
                        key={a.id}
                        className="border-b border-[#1A1A1A] hover:bg-[#0F1318] transition-colors"
                      >
                        <td className="px-4 py-2.5 text-[#6B7280] font-mono">#{a.id}</td>
                        <td className="px-4 py-2.5">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              a.alert_type?.toLowerCase() === 'danger'
                                ? 'bg-[#EF4444]/10 text-[#EF4444]'
                                : 'bg-[#F59E0B]/10 text-[#F59E0B]'
                            }`}
                          >
                            {(a.alert_type ?? 'warning').toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-[#9CA3AF]">{a.camera_name ?? '—'}</td>
                        <td className="px-4 py-2.5 text-[#9CA3AF] font-mono whitespace-nowrap">
                          {a.triggered_at ? new Date(a.triggered_at).toLocaleTimeString() : '—'}
                        </td>
                        <td className="px-4 py-2.5">
                          {isOpen ? (
                            <span className="text-[#EF4444]">🔴 Open</span>
                          ) : (
                            <span className="text-[#10B981]">✅ Done</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Mobile app info box */}
          <div className="bg-[#0B0F19] border border-[#1F2937] rounded p-4 flex flex-col gap-3 mt-2">
            <h3 className="text-white text-xs font-semibold uppercase tracking-wide">
              📱 How Guards Use the Mobile App
            </h3>
            <ul className="text-[#9CA3AF] text-xs space-y-2">
              <li>
                <span className="text-[#3B82F6] font-medium">Login →</span>{' '}
                Guard enters email + password. JWT token stored securely on device.
              </li>
              <li>
                <span className="text-[#F59E0B] font-medium">Alerts →</span>{' '}
                Pushed instantly via Firebase (FCM). Guard receives notification even when app is closed.
              </li>
              <li>
                <span className="text-[#10B981] font-medium">Camera Feeds →</span>{' '}
                Guard sees only cameras assigned to them or shared ones. MJPEG stream via this backend.
              </li>
              <li>
                <span className="text-[#EF4444] font-medium">Acknowledge →</span>{' '}
                Guard taps alert → resolved in DB → removed from all devices instantly.
              </li>
            </ul>
            <p className="text-[10px] text-[#4B5563] border-t border-[#1F2937] pt-2 mt-1">
              To control what guards see: assign cameras on the CCTV Manager page. To block a guard's access: deactivate their account in User Management or Sessions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
