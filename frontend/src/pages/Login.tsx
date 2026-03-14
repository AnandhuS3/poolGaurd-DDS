/**
 * Login.tsx
 * Authentication page.
 */

import { useState, useEffect, type FormEvent } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function Login() {
  const { login, isLoading, token } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const justRegistered = (location.state as { registered?: boolean } | null)?.registered === true;
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // Navigate only after the token state has actually been committed by React.
  // Calling navigate() immediately after `await login()` can race against
  // React flushing the setToken/setUser updates, causing ProtectedLayout to
  // see token=null and redirect back to /login.
  useEffect(() => {
    if (token) navigate('/', { replace: true });
  }, [token, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
      // Navigation is handled by the useEffect above once token is set.
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white tracking-widest uppercase">PoolGuard</h1>
          <p className="text-[#9CA3AF] text-sm mt-1">Drowning Detection System</p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-[#121212] border border-[#1F2937] rounded p-6 flex flex-col gap-4"
        >
          <h2 className="text-white font-semibold text-sm uppercase tracking-wide">Sign In</h2>

          {justRegistered && (
            <div className="bg-[#34C759]/10 border border-[#34C759]/30 text-[#34C759] text-xs rounded p-3">
              Account created — sign in to continue.
            </div>
          )}

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

          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="mt-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded transition-colors"
          >
            {isLoading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-[#6B7280] text-xs mt-4">
          Default admin: creagoouon@gmail.com / Admin1234
        </p>
        <p className="text-center text-[#6B7280] text-xs mt-2">
          Don't have an account?{' '}
          <Link to="/register" className="text-[#3B82F6] hover:underline">
            Register
          </Link>
        </p>
        <p className="text-center text-[#6B7280] text-xs mt-1">
          <Link to="/forgot-password" className="text-[#3B82F6] hover:underline">
            Forgot password?
          </Link>
        </p>
      </div>
    </div>
  );
}
