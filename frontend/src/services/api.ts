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

const api: AxiosInstance = axios.create({
  // All paths go through Vite proxy → http://localhost:8000
  baseURL: '/',
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
