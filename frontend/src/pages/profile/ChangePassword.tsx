/**
 * ChangePassword.tsx
 * Change current user password — POST /api/auth/change-password
 */

import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import api from '../../services/api';

export function ChangePassword() {
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (form.new_password.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    if (!/[A-Z]/.test(form.new_password)) {
      setError('New password must contain at least one uppercase letter.');
      return;
    }
    if (!/[0-9]/.test(form.new_password)) {
      setError('New password must contain at least one digit.');
      return;
    }
    if (form.new_password !== form.confirm) {
      setError('Passwords do not match.');
      return;
    }
    setIsLoading(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: form.old_password,
        new_password: form.new_password,
      });
      setSuccess('Password changed successfully.');
      setForm({ old_password: '', new_password: '', confirm: '' });
    } catch (err: unknown) {
      setError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) ?? 'Failed to change password'
          : 'Failed to change password',
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-lg mx-auto flex flex-col gap-6">
        <div>
          <h1 className="text-white font-semibold text-base">Change Password</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">Update your account password.</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-[#121212] border border-[#1F2937] rounded p-6 flex flex-col gap-4"
        >
          {error && (
            <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/40 text-[#FF3B30] text-xs rounded p-3">
              {error}
            </div>
          )}
          {success && (
            <div className="bg-[#34C759]/10 border border-[#34C759]/40 text-[#34C759] text-xs rounded p-3">
              {success}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Current Password</label>
            <input
              type="password"
              required
              value={form.old_password}
              onChange={set('old_password')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="••••••••"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">New Password</label>
            <input
              type="password"
              required
              value={form.new_password}
              onChange={set('new_password')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="Min 8 chars, 1 uppercase, 1 digit"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Confirm New Password</label>
            <input
              type="password"
              required
              value={form.confirm}
              onChange={set('confirm')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="••••••••"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded transition-colors"
            >
              {isLoading ? 'Updating…' : 'Update Password'}
            </button>
            <Link to="/profile" className="text-xs text-[#6B7280] hover:text-white transition-colors">
              ← Back to Profile
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
