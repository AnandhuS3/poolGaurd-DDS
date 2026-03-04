/**
 * api.ts
 * Centralized Axios instance with:
 * - Auth token injection on every request
 * - 401 → auto-logout handler
 *
 * Usage:
 *   import api from '../services/api';
 *   api.get('/api/admin/users');
 */

import axios, { type AxiosInstance } from 'axios';

const TOKEN_KEY = 'dds_token';

/** Call setLogoutHandler(logout) once AuthContext mounts */
let _onUnauthorized: (() => void) | null = null;

export function setLogoutHandler(fn: () => void) {
  _onUnauthorized = fn;
}

// Resolve the backend base URL:
//   1. VITE_API_URL env var — set this in Railway frontend service variables (takes priority)
//   2. If running on *.railway.app (production) but the env var wasn't set, fall back to the
//      known Railway backend URL so the app works without any dashboard configuration.
//   3. Otherwise ('/' — localhost dev) let the Vite proxy route /api → localhost:8000.
const _railwayBackend = 'https://backend-production-d7e4c.up.railway.app';
const _isRailway =
  typeof window !== 'undefined' &&
  window.location.hostname !== 'localhost' &&
  window.location.hostname !== '127.0.0.1';
const _baseURL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ||
  (_isRailway ? _railwayBackend : '/');

const api: AxiosInstance = axios.create({
  baseURL: _baseURL,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor ──────────────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor ─────────────────────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      _onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

export default api;
