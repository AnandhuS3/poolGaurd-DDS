/**
 * Sessions.tsx
 * View active sessions with Deactivate/Activate guard control — Admin only.
 * GET /api/admin/sessions
 * PATCH /api/admin/users/{id}  ← deactivate / reactivate
 */

import { useEffect, useState } from 'react';
import api from '../../services/api';
import { parseApiError } from '../../services/parseApiError';

interface SessionRecord {
  id?: number;
  name: string;
  email: string;
  role: string;
  login_time: string;
  ip_address?: string;
}

interface AdminUser {
  id: number;
  email: string;
  is_active: boolean;
}

export function Sessions() {
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [togglingEmail, setTogglingEmail] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const [sessRes, usersRes] = await Promise.all([
        api.get<SessionRecord[]>('/api/admin/sessions'),
        api.get<AdminUser[]>('/api/admin/users'),
      ]);
      setSessions(sessRes.data ?? []);
      setUsers(usersRes.data ?? []);
    } catch {
      setError('Failed to load sessions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30_000);
    return () => clearInterval(id);
  }, []);

  /** Find user record for a session by email */
  const getUserForSession = (email: string) =>
    users.find((u) => u.email === email);

  const toggleActive = async (session: SessionRecord) => {
    const user = getUserForSession(session.email);
    if (!user) return;

    const willDeactivate = user.is_active;
    const action = willDeactivate ? 'deactivate' : 'reactivate';
    if (
      !window.confirm(
        `${action.charAt(0).toUpperCase() + action.slice(1)} "${session.name}"? ` +
          (willDeactivate
            ? 'This will prevent them from accessing the mobile app on next request.'
            : 'This will allow them to log in again.')
      )
    )
      return;

    setTogglingEmail(session.email);
    try {
      await api.patch(`/api/admin/users/${user.id}`, { is_active: !user.is_active });
      // Refresh
      const usersRes = await api.get<AdminUser[]>('/api/admin/users');
      setUsers(usersRes.data ?? []);
    } catch (err) {
      alert(parseApiError(err, `Failed to ${action} user`));
    } finally {
      setTogglingEmail(null);
    }
  };

  const guardSessions = sessions.filter((s) => s.role === 'guard');
  const adminSessions = sessions.filter((s) => s.role === 'admin');

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-white font-semibold text-base">Active Sessions</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">
            Currently logged-in users. Auto-refreshes every 30s.{' '}
            <span className="text-[#4B5563]">
              Deactivating a user blocks their next API request (mobile app access).
            </span>
          </p>
        </div>
        <button
          onClick={fetchData}
          className="px-3 py-1.5 bg-[#1F2937] hover:bg-[#374151] text-[#9CA3AF] hover:text-white text-xs rounded transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      {/* Summary row */}
      {!isLoading && !error && (
        <div className="flex gap-4 text-xs">
          <span className="text-[#10B981]">● {guardSessions.length} guard{guardSessions.length !== 1 ? 's' : ''} online</span>
          <span className="text-[#3B82F6]">● {adminSessions.length} admin{adminSessions.length !== 1 ? 's' : ''} online</span>
          <span className="text-[#6B7280]">Total: {sessions.length}</span>
        </div>
      )}

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
                {['User', 'Email', 'Role', 'Login Time', 'IP Address', 'Account Status', 'Action'].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-[#9CA3AF] text-xs uppercase tracking-wide font-medium"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {sessions.map((s, i) => {
                const matchedUser = getUserForSession(s.email);
                const isActive = matchedUser?.is_active ?? true;
                const isToggling = togglingEmail === s.email;

                return (
                  <tr
                    key={i}
                    className={`border-b border-[#1A1A1A] hover:bg-[#0F1318] transition-colors ${
                      !isActive ? 'opacity-60' : ''
                    }`}
                  >
                    <td className="px-4 py-3 text-white font-medium">{s.name}</td>
                    <td className="px-4 py-3 text-[#9CA3AF]">{s.email}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] uppercase tracking-wide font-medium ${
                          s.role === 'admin'
                            ? 'bg-[#3B82F6]/10 text-[#3B82F6]'
                            : 'bg-[#1F2937] text-[#9CA3AF]'
                        }`}
                      >
                        {s.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#9CA3AF] font-mono text-xs">
                      {s.login_time ? new Date(s.login_time).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-[#9CA3AF] font-mono text-xs">
                      {s.ip_address ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                          isActive
                            ? 'bg-[#10B981]/10 text-[#10B981]'
                            : 'bg-[#EF4444]/10 text-[#EF4444]'
                        }`}
                      >
                        {isActive ? 'Active' : 'Deactivated'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {matchedUser ? (
                        <button
                          onClick={() => toggleActive(s)}
                          disabled={isToggling}
                          className={`text-xs font-medium disabled:opacity-50 transition-colors ${
                            isActive
                              ? 'text-[#EF4444] hover:text-[#DC2626]'
                              : 'text-[#10B981] hover:text-[#059669]'
                          }`}
                        >
                          {isToggling
                            ? 'Updating…'
                            : isActive
                            ? 'Deactivate'
                            : 'Reactivate'}
                        </button>
                      ) : (
                        <span className="text-[#4B5563] text-xs">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
