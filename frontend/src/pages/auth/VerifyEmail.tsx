/**
 * VerifyEmail.tsx
 * Landed on via GET /verify-email?token=<token> link in the user's inbox.
 * Calls POST /api/auth/verify-email and shows success / error.
 */

import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import api from '../../services/api';
import axios from 'axios';

type State = 'loading' | 'success' | 'error';

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [state, setState] = useState<State>('loading');
  const [message, setMessage] = useState('');
  const [userName, setUserName] = useState('');

  useEffect(() => {
    if (!token) {
      setState('error');
      setMessage('No verification token found in the link. Please check your email again.');
      return;
    }

    api
      .get(`/api/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then((res) => {
        setState('success');
        setUserName(res.data.name ?? '');
        setMessage(res.data.message ?? 'Email verified successfully.');
      })
      .catch((err: unknown) => {
        setState('error');
        const detail = axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) ?? 'Verification failed.'
          : 'Verification failed.';
        setMessage(detail);
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
      <div className="w-full max-w-sm text-center space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-widest uppercase">PoolGuard</h1>
          <p className="text-[#9CA3AF] text-sm mt-1">Drowning Detection System</p>
        </div>

        <div className="bg-[#121212] border border-[#1F2937] rounded p-8 flex flex-col items-center gap-4">
          {state === 'loading' && (
            <>
              <div className="text-4xl animate-pulse">⏳</div>
              <p className="text-[#9CA3AF] text-sm">Verifying your email…</p>
            </>
          )}

          {state === 'success' && (
            <>
              <div className="text-5xl">✅</div>
              <h2 className="text-white font-semibold text-lg">Email Verified!</h2>
              {userName && (
                <p className="text-[#9CA3AF] text-sm">Welcome, <span className="text-white font-medium">{userName}</span>!</p>
              )}
              <p className="text-[#9CA3AF] text-sm">{message}</p>
              <Link
                to="/login"
                className="mt-2 inline-block bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-semibold px-6 py-2.5 rounded transition-colors"
              >
                Sign In
              </Link>
            </>
          )}

          {state === 'error' && (
            <>
              <div className="text-5xl">❌</div>
              <h2 className="text-white font-semibold text-lg">Verification Failed</h2>
              <p className="text-[#FF3B30] text-sm">{message}</p>
              <Link
                to="/register"
                className="mt-2 inline-block border border-[#3B82F6] text-[#3B82F6] hover:bg-[#3B82F6] hover:text-white text-sm font-semibold px-6 py-2.5 rounded transition-colors"
              >
                Register Again
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
