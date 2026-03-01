/**
 * Sessions.tsx
 * View active sessions — Admin only.
 * GET /api/admin/sessions
 */

import { useEffect, useState } from 'react';
import api from '../../services/api';

interface SessionRecord {
  id?: number;
  name: string;
  email: string;
  role: string;
  login_time: string;
  ip_address?: string;
}

export function Sessions() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchSessions = async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await api.get<SessionRecord[]>('/api/admin/sessions');
      setSessions(res.data ?? []);
    } catch {
      setError('Failed to load sessions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
    // Poll every 30 seconds
    const id = setInterval(fetchSessions, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-white font-semibold text-base">Active Sessions</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">Currently logged-in users. Refreshes every 30s.</p>
        </div>
        <button
          onClick={fetchSessions}
          className="px-3 py-1.5 bg-[#1F2937] hover:bg-[#374151] text-[#9CA3AF] hover:text-white text-xs rounded transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="bg-[#121212] border border-[#1F2937] rounded overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-[#9CA3AF] text-sm">Loading…</div>
        ) : error ? (
          <div className="p-8 text-center text-[#FF3B30] text-sm">{error}</div>
        ) : sessions.length === 0 ? (
          <div className="p-8 text-center text-[#6B7280] text-sm">No active sessions.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1F2937]">
                {['User', 'Email', 'Role', 'Login Time', 'IP Address'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-[#9CA3AF] text-xs uppercase tracking-wide font-medium"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sessions.map((s, i) => (
                <tr key={i} className="border-b border-[#1A1A1A] hover:bg-[#0F1318] transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{s.name}</td>
                  <td className="px-4 py-3 text-[#9CA3AF]">{s.email}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-[#1F2937] text-[#9CA3AF] text-[11px] rounded uppercase tracking-wide">
                      {s.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-[#9CA3AF] font-mono text-xs">
                    {s.login_time ? new Date(s.login_time).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-[#9CA3AF] font-mono text-xs">
                    {s.ip_address ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-[#4B5563] text-xs">
        Total active: <span className="text-[#9CA3AF]">{sessions.length}</span>
      </p>
    </div>
  );
}
