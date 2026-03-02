/**
 * ResetPassword.tsx
 * Landed on via the reset link from the email.
 * Lets the user choose a new password.
 */

import { useState, type FormEvent } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import axios from 'axios';

function passwordStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const map = [
    { label: '', color: '#1F2937' },
    { label: 'Weak', color: '#FF3B30' },
    { label: 'Fair', color: '#FF9500' },
    { label: 'Good', color: '#FFCC00' },
    { label: 'Strong', color: '#34C759' },
  ];
  return { score, ...map[score] };
}

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const strength = passwordStrength(password);

  const validate = (): string => {
    if (password.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Z]/.test(password)) return 'Password must contain at least one uppercase letter.';
    if (!/[0-9]/.test(password)) return 'Password must contain at least one digit.';
    if (password !== confirm) return 'Passwords do not match.';
    return '';
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const err = validate();
    if (err) { setError(err); return; }

    if (!token) {
      setError('Invalid reset link. Please request a new one.');
      return;
    }

    setIsLoading(true);
    try {
      await api.post('/api/auth/reset-password', { token, new_password: password });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e)
        ? (e.response?.data?.detail as string) ?? 'Failed to reset password.'
        : 'Failed to reset password.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white tracking-widest uppercase">PoolGuard</h1>
          <p className="text-[#9CA3AF] text-sm mt-1">Drowning Detection System</p>
        </div>

        {success ? (
          <div className="bg-[#121212] border border-[#1F2937] rounded p-8 flex flex-col items-center gap-4 text-center">
            <div className="text-5xl">🔐</div>
            <h2 className="text-white font-semibold text-lg">Password Reset!</h2>
            <p className="text-[#9CA3AF] text-sm">
              Your password has been updated. Redirecting to sign-in…
            </p>
            <Link to="/login" className="text-[#3B82F6] hover:underline text-sm">
              Go to sign in now
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="bg-[#121212] border border-[#1F2937] rounded p-6 flex flex-col gap-4"
          >
            <h2 className="text-white font-semibold text-sm uppercase tracking-wide">Choose New Password</h2>

            {error && (
              <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/40 text-[#FF3B30] text-xs rounded p-3">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">New Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
                placeholder="Min 8 chars, 1 uppercase, 1 digit"
              />
              {password && (
                <div className="flex flex-col gap-1 mt-1">
                  <div className="h-1 bg-[#1F2937] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{ width: `${(strength.score / 4) * 100}%`, backgroundColor: strength.color }}
                    />
                  </div>
                  <span className="text-[11px]" style={{ color: strength.color }}>{strength.label}</span>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Confirm Password</label>
              <input
                type="password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !token}
              className="mt-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded transition-colors"
            >
              {isLoading ? 'Saving…' : 'Reset Password'}
            </button>

            {!token && (
              <p className="text-[#FF3B30] text-xs text-center">
                Invalid link.{' '}
                <Link to="/forgot-password" className="underline">Request a new one</Link>.
              </p>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
