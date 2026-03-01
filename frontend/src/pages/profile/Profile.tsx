/**
 * Profile.tsx
 * Update current user's profile — PUT /api/auth/profile
 */

import { useState, type FormEvent, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

export function Profile() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({ name: '', email: '', phone_number: '' });
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Populate form with current user data
  useEffect(() => {
    if (user) {
      setForm({
        name: user.name ?? '',
        email: user.email ?? '',
        phone_number: user.phone_number ?? '',
      });
    }
  }, [user]);

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!form.name.trim() || form.name.trim().length < 2) {
      setError('Name must be at least 2 characters.');
      return;
    }
    setIsLoading(true);
    try {
      await api.put('/api/auth/profile', {
        name: form.name.trim(),
        email: form.email,
        phone_number: form.phone_number || undefined,
      });
      await refreshUser();
      setSuccess('Profile updated successfully.');
    } catch (err: unknown) {
      setError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) ?? 'Update failed'
          : 'Update failed',
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-lg mx-auto flex flex-col gap-6">
        <div>
          <h1 className="text-white font-semibold text-base">My Profile</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">Update your account details.</p>
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

          {/* Role badge (read-only) */}
          {user?.role && (
            <div className="flex items-center gap-2">
              <span className="text-[#9CA3AF] text-xs uppercase tracking-wide">Role</span>
              <span className="px-2 py-0.5 bg-[#1F2937] text-[#9CA3AF] text-[11px] rounded uppercase tracking-wide">
                {user.role}
              </span>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Full Name</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={set('name')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Email</label>
            <input
              type="email"
              required
              value={form.email}
              onChange={set('email')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Phone</label>
            <input
              type="tel"
              value={form.phone_number}
              onChange={set('phone_number')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="+91 9876543210"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded transition-colors"
            >
              {isLoading ? 'Saving…' : 'Save Changes'}
            </button>
            <Link
              to="/profile/change-password"
              className="text-xs text-[#3B82F6] hover:underline"
            >
              Change password →
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
