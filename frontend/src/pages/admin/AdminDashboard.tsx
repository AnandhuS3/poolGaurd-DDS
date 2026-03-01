/**
 * AdminDashboard.tsx
 * Admin overview — shows quick links and summary stats.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';

interface Stats {
  users: number;
  sessions: number;
  alerts: number;
}

export function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    // Fetch counts in parallel (best-effort)
    Promise.all([
      api.get('/api/admin/users').catch(() => ({ data: [] })),
      api.get('/api/admin/sessions').catch(() => ({ data: [] })),
      api.get('/api/admin/alerts?limit=1000').catch(() => ({ data: [] })),
    ]).then(([u, s, a]) => {
      setStats({
        users: Array.isArray(u.data) ? u.data.length : 0,
        sessions: Array.isArray(s.data) ? s.data.length : 0,
        alerts: Array.isArray(a.data) ? a.data.length : 0,
      });
    });
  }, []);

  const tiles = [
    { label: 'Total Users', value: stats?.users ?? '—', to: '/admin/users' },
    { label: 'Active Sessions', value: stats?.sessions ?? '—', to: '/admin/sessions' },
    { label: 'Total Alerts', value: stats?.alerts ?? '—', to: '/admin/alerts' },
  ];

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-white font-semibold text-base">Admin Dashboard</h1>
        <p className="text-[#9CA3AF] text-sm mt-0.5">System overview and quick access.</p>
      </div>

      {/* Stats tiles */}
      <div className="grid grid-cols-3 gap-4">
        {tiles.map(({ label, value, to }) => (
          <Link
            key={to}
            to={to}
            className="bg-[#121212] border border-[#1F2937] rounded p-5 hover:border-[#374151] transition-colors flex flex-col gap-2"
          >
            <span className="text-[#9CA3AF] text-xs uppercase tracking-wide">{label}</span>
            <span className="text-2xl font-bold text-white">{value}</span>
          </Link>
        ))}
      </div>

      {/* Quick links */}
      <div className="bg-[#121212] border border-[#1F2937] rounded p-5 flex flex-col gap-3">
        <h2 className="text-white text-sm font-semibold uppercase tracking-wide">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link
            to="/admin/users"
            className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] text-white text-xs rounded transition-colors"
          >
            Manage Users
          </Link>
          <Link
            to="/admin/system-admin"
            className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] text-white text-xs rounded transition-colors"
          >
            System Admin Settings
          </Link>
          <Link
            to="/admin/sessions"
            className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] text-white text-xs rounded transition-colors"
          >
            View Sessions
          </Link>
          <Link
            to="/admin/alerts"
            className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] text-white text-xs rounded transition-colors"
          >
            Alert History
          </Link>
        </div>
      </div>
    </div>
  );
}
