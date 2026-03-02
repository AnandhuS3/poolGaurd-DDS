/**
 * ForgotPassword.tsx
 * Lets the user request a password-reset email.
 */

import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import axios from 'axios';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await api.post('/api/auth/forgot-password', { email });
      setSent(true);
    } catch (err: unknown) {
      // 202 is considered success by axios; real errors are 4xx/5xx
      if (axios.isAxiosError(err) && err.response?.status === 202) {
        setSent(true);
      } else {
        setError('Something went wrong. Please try again.');
      }
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

        {sent ? (
          <div className="bg-[#121212] border border-[#1F2937] rounded p-8 flex flex-col items-center gap-4 text-center">
            <div className="text-5xl">📬</div>
            <h2 className="text-white font-semibold text-lg">Check your inbox</h2>
            <p className="text-[#9CA3AF] text-sm leading-relaxed">
              If <span className="text-[#3B82F6] font-medium">{email}</span> is registered,
              we sent a password-reset link. It expires in 30&nbsp;minutes.
            </p>
            <Link to="/login" className="text-[#3B82F6] hover:underline text-sm">
              Back to sign in
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="bg-[#121212] border border-[#1F2937] rounded p-6 flex flex-col gap-4"
          >
            <h2 className="text-white font-semibold text-sm uppercase tracking-wide">Reset Password</h2>
            <p className="text-[#9CA3AF] text-xs leading-relaxed">
              Enter the email address associated with your account and we'll send you a link to reset your password.
            </p>

            {error && (
              <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/40 text-[#FF3B30] text-xs rounded p-3">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
                placeholder="you@example.com"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded transition-colors"
            >
              {isLoading ? 'Sending…' : 'Send Reset Link'}
            </button>
          </form>
        )}

        <p className="text-center text-[#6B7280] text-xs">
          Remembered it?{' '}
          <Link to="/login" className="text-[#3B82F6] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
