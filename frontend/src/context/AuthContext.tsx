/**
 * AuthContext.tsx
 * Provides auth state globally. Persists token to localStorage.
 *
 * On mount:
 *   - If token exists in localStorage → call GET /api/auth/me to validate
 *     and refresh user data (picks up role/status changes server-side).
 *   - Registers auto-logout handler on the centralized api instance so any
 *     401 response anywhere triggers logout automatically.
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import api, { setLogoutHandler } from '../services/api';
import type { AuthUser, AuthTokens } from '../types/detection';

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = 'dds_token';
const USER_KEY = 'dds_user';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const raw = localStorage.getItem(USER_KEY);
      // Guard against the literal string "undefined" stored by a previous bug
      if (!raw || raw === 'undefined' || raw === 'null') return null;
      return JSON.parse(raw) as AuthUser;
    } catch {
      localStorage.removeItem(USER_KEY);
      return null;
    }
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [isLoading, setIsLoading] = useState(!!localStorage.getItem(TOKEN_KEY));
  const [error, setError] = useState<string | null>(null);

  // ── Logout ──────────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }, []);

  // ── Register api-level auto-logout on 401 ───────────────────────────────────
  useEffect(() => {
    setLogoutHandler(logout);
  }, [logout]);

  // ── Sync axios default header (keeps axios.post('/analyze/…') working) ─────
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // ── On app load: validate stored token via /me ──────────────────────────────
  useEffect(() => {
    if (!token) {
      setIsLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get<AuthUser>('/api/auth/me');
        if (!cancelled) {
          setUser(res.data);
          if (res.data) localStorage.setItem(USER_KEY, JSON.stringify(res.data));
        }
      } catch {
        if (!cancelled) logout();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Login ────────────────────────────────────────────────────────────────────
  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.post<AuthTokens>('/api/auth/login', { email, password });
      const { access_token, user: u } = res.data;
      setToken(access_token);
      setUser(u);
      localStorage.setItem(TOKEN_KEY, access_token);
      if (u) localStorage.setItem(USER_KEY, JSON.stringify(u));
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err)
          ? (err.response?.data?.detail as string) ?? 'Login failed'
          : 'Login failed';
      setError(msg);
      throw new Error(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // ── refreshUser ──────────────────────────────────────────────────────────────
  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      const res = await api.get<AuthUser>('/api/auth/me');
      setUser(res.data);
      if (res.data) localStorage.setItem(USER_KEY, JSON.stringify(res.data));
    } catch {
      logout();
    }
  }, [token, logout]);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, error, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
