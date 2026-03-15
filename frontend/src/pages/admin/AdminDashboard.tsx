/**
 * AdminDashboard.tsx
 * Admin overview — live system stats + quick access.
 */

import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';

interface Stats {
  totalUsers: number;
  activeGuards: number;       // guards currently logged in
  totalCameras: number;
  activeCameras: number;
  inactiveCameras: number;
  totalAlerts: number;
  unresolvedAlerts: number;
}

interface Camera {
  id: number;
  camera_name: string;
  status: 'active' | 'inactive' | 'maintenance';
}

interface Session {
  id?: number;
  name: string;
  role: string;
  login_time: string;
}

interface AlertRecord {
  id: number;
  resolved_at?: string | null;
}

export function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStats = useCallback(async () => {
    setRefreshing(true);
    try {
      const [usersRes, sessionsRes, alertsRes, camerasRes] = await Promise.all([
        api.get<{ id: number; role: string; is_active: boolean }[]>('/api/admin/users').catch(() => ({ data: [] })),
        api.get<Session[]>('/api/admin/sessions').catch(() => ({ data: [] })),
        api.get<AlertRecord[]>('/api/admin/alerts?limit=1000').catch(() => ({ data: [] })),
        api.get<Camera[]>('/api/cameras').catch(() => ({ data: [] })),
      ]);

      const users = usersRes.data ?? [];
      const sessions = sessionsRes.data ?? [];
      const alerts = alertsRes.data ?? [];
      const cameras = camerasRes.data ?? [];

      setStats({
        totalUsers: users.length,
        activeGuards: sessions.filter((s) => s.role === 'guard').length,
        totalCameras: cameras.length,
        activeCameras: cameras.filter((c) => c.status === 'active').length,
        inactiveCameras: cameras.filter((c) => c.status !== 'active').length,
        totalAlerts: alerts.length,
        unresolvedAlerts: alerts.filter((a) => !a.resolved_at).length,
      });
      setLastUpdated(new Date());
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const id = setInterval(fetchStats, 30_000);
    return () => clearInterval(id);
  }, [fetchStats]);

  const statTiles = stats
    ? [
        {
          label: 'Total Users',
          value: stats.totalUsers,
          sub: `${stats.activeGuards} guards online`,
          color: 'text-[#3B82F6]',
          to: '/admin/users',
          icon: '👤',
        },
        {
          label: 'Cameras',
          value: stats.totalCameras,
          sub: `${stats.activeCameras} active · ${stats.inactiveCameras} offline`,
          color: stats.inactiveCameras > 0 ? 'text-[#F59E0B]' : 'text-[#10B981]',
          to: '/admin/cctv-manager',
          icon: '📷',
        },
        {
          label: 'Active Sessions',
          value: stats.activeGuards,
          sub: 'guards currently logged in',
          color: stats.activeGuards > 0 ? 'text-[#10B981]' : 'text-[#6B7280]',
          to: '/admin/sessions',
          icon: '🟢',
        },
        {
          label: 'Open Alerts',
          value: stats.unresolvedAlerts,
          sub: `${stats.totalAlerts} total recorded`,
          color: stats.unresolvedAlerts > 0 ? 'text-[#EF4444]' : 'text-[#10B981]',
          to: '/admin/alerts',
          icon: '🚨',
        },
      ]
    : [];

  return (
    <div className="p-6 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-white font-semibold text-base">Admin Dashboard</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">
            System overview — auto-refreshes every 30s.
            {lastUpdated && (
              <span className="ml-2 text-[#4B5563]">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>
        <button
          onClick={fetchStats}
          disabled={refreshing}
          className="px-3 py-1.5 bg-[#1F2937] hover:bg-[#374151] disabled:opacity-50 text-[#9CA3AF] hover:text-white text-xs rounded transition-colors"
        >
          {refreshing ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </div>

      {/* Stats tiles */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {stats === null
          ? Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="bg-[#121212] border border-[#1F2937] rounded p-5 animate-pulse h-24"
              />
            ))
          : statTiles.map(({ label, value, sub, color, to, icon }) => (
              <Link
                key={to}
                to={to}
                className="bg-[#121212] border border-[#1F2937] rounded p-5 hover:border-[#374151] transition-colors flex flex-col gap-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF] text-xs uppercase tracking-wide">{label}</span>
                  <span className="text-base">{icon}</span>
                </div>
                <span className={`text-3xl font-bold ${color}`}>{value}</span>
                <span className="text-[#6B7280] text-xs">{sub}</span>
              </Link>
            ))}
      </div>

      {/* Camera health bar */}
      {stats && stats.totalCameras > 0 && (
        <div className="bg-[#121212] border border-[#1F2937] rounded p-5 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h2 className="text-white text-sm font-semibold">Camera Health</h2>
            <Link to="/admin/cctv-manager" className="text-xs text-[#3B82F6] hover:underline">
              Manage →
            </Link>
          </div>
          <div className="flex rounded overflow-hidden h-3 bg-[#1F2937]">
            <div
              className="bg-[#10B981] transition-all"
              style={{ width: `${(stats.activeCameras / stats.totalCameras) * 100}%` }}
            />
            <div
              className="bg-[#EF4444] transition-all"
              style={{ width: `${(stats.inactiveCameras / stats.totalCameras) * 100}%` }}
            />
          </div>
          <div className="flex gap-4 text-xs">
            <span className="text-[#10B981]">● {stats.activeCameras} Active (AI running)</span>
            <span className="text-[#EF4444]">● {stats.inactiveCameras} Offline / Paused</span>
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="bg-[#121212] border border-[#1F2937] rounded p-5 flex flex-col gap-3">
        <h2 className="text-white text-sm font-semibold uppercase tracking-wide">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          {[
            { to: '/admin/users', label: '👤 Manage Guards' },
            { to: '/admin/cctv-manager', label: '📷 CCTV Cameras' },
            { to: '/admin/guard-monitor', label: '📱 Guard Monitor' },
            { to: '/admin/sessions', label: '🟢 Active Sessions' },
            { to: '/admin/alerts', label: '🚨 Alert History' },
            { to: '/admin/system-admin', label: '⚙️ System Admin' },
          ].map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] text-white text-xs rounded transition-colors"
            >
              {label}
            </Link>
          ))}
        </div>
      </div>

      {/* How the mobile app works */}
      <div className="bg-[#121212] border border-[#1F2937] rounded p-5 flex flex-col gap-3">
        <h2 className="text-white text-sm font-semibold uppercase tracking-wide">
          📱 Mobile App — How It Works
        </h2>
        <div className="grid grid-cols-2 gap-4 text-xs text-[#9CA3AF]">
          {[
            {
              title: 'Login',
              desc: 'Guard logs in with email/password. JWT token stored securely on device.',
            },
            {
              title: 'Live Alerts',
              desc: 'Alerts pushed via FCM (Firebase) in real-time. Guard also polls /api/alerts/active on open.',
            },
            {
              title: 'Camera Feeds',
              desc: 'Guard sees only cameras assigned to them or unassigned ones. Streams via MJPEG proxy.',
            },
            {
              title: 'Acknowledge',
              desc: 'Guard taps alert → marks resolved via /api/alerts/{id}/acknowledge → removed from all devices.',
            },
          ].map(({ title, desc }) => (
            <div key={title} className="bg-[#0B0F19] border border-[#1F2937] rounded p-3 flex flex-col gap-1.5">
              <span className="text-white font-medium">{title}</span>
              <span>{desc}</span>
            </div>
          ))}
        </div>
        <p className="text-[#4B5563] text-xs">
          Admin controls camera visibility (assign guard to camera), guard registration, and alert resolution from this dashboard.
        </p>
      </div>
    </div>
  );
}
