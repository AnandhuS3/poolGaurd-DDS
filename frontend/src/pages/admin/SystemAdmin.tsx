/**
 * SystemAdmin.tsx
 * View and change system administrator details — Admin only.
 *
 * GET   /api/admin/system-admin
 * PATCH /api/admin/system-admin/password
 */

import { useEffect, useState, type FormEvent } from 'react';
import axios from 'axios';
import api from '../../services/api';

interface SystemAdminInfo {
  id: number;
  name: string;
  email: string;
  phone_number?: string;
  role: string;
  is_active: boolean;
}

export function SystemAdmin() {
  const [adminInfo, setAdminInfo] = useState<SystemAdminInfo | null>(null);
  const [loadError, setLoadError] = useState('');
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');

  useEffect(() => {
    api
      .get<SystemAdminInfo>('/api/admin/system-admin')
      .then((r) => setAdminInfo(r.data))
      .catch(() => setLoadError('Failed to load system administrator info.'));
  }, []);

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handlePasswordSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setPwError('');
    setPwSuccess('');
    if (form.new_password.length < 8) {
      setPwError('New password must be at least 8 characters.');
      return;
    }
    if (form.new_password !== form.confirm) {
      setPwError('Passwords do not match.');
      return;
    }
    setPwLoading(true);
    try {
      await api.patch('/api/admin/system-admin/password', {
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setPwSuccess('System admin password updated successfully.');
      setForm({ current_password: '', new_password: '', confirm: '' });
    } catch (err: unknown) {
      setPwError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) ?? 'Password update failed'
          : 'Password update failed',
      );
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-white font-semibold text-base">System Admin Control</h1>
        <p className="text-[#9CA3AF] text-sm mt-0.5">
          Protected system administrator account. Cannot be deleted.
        </p>
      </div>

      {/* Info card */}
      {loadError ? (
        <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/40 text-[#FF3B30] text-xs rounded p-4">
          {loadError}
        </div>
      ) : adminInfo ? (
        <div className="bg-[#121212] border border-[#1F2937] rounded p-5 flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-widest text-[#4B5563]">
              System Administrator
            </span>
            <span className="px-2 py-0.5 bg-[#34C759]/10 text-[#34C759] text-[11px] rounded">
              Protected
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Field label="Name" value={adminInfo.name} />
            <Field label="Email" value={adminInfo.email} />
            <Field label="Phone" value={adminInfo.phone_number ?? '—'} />
            <Field label="Role" value={adminInfo.role.toUpperCase()} />
          </div>
        </div>
      ) : (
        <div className="text-[#9CA3AF] text-sm">Loading…</div>
      )}

      {/* Change password */}
      <div className="bg-[#121212] border border-[#1F2937] rounded p-5 flex flex-col gap-4">
        <h2 className="text-white text-sm font-semibold uppercase tracking-wide">
          Change System Admin Password
        </h2>

        {pwError && (
          <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/40 text-[#FF3B30] text-xs rounded p-3">
            {pwError}
          </div>
        )}
        {pwSuccess && (
          <div className="bg-[#34C759]/10 border border-[#34C759]/40 text-[#34C759] text-xs rounded p-3">
            {pwSuccess}
          </div>
        )}

        <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-3 max-w-sm">
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Current Password</label>
            <input
              type="password"
              required
              value={form.current_password}
              onChange={set('current_password')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">New Password</label>
            <input
              type="password"
              required
              value={form.new_password}
              onChange={set('new_password')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
              placeholder="Min 8 characters"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Confirm New Password</label>
            <input
              type="password"
              required
              value={form.confirm}
              onChange={set('confirm')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
            />
          </div>
          <button
            type="submit"
            disabled={pwLoading}
            className="mt-1 px-5 py-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white text-sm font-semibold rounded transition-colors"
          >
            {pwLoading ? 'Updating…' : 'Update Password'}
          </button>
        </form>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[#6B7280] text-[11px] uppercase tracking-wide">{label}</span>
      <span className="text-white text-sm">{value}</span>
    </div>
  );
}
