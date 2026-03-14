/**
 * parseApiError.ts
 * Safely converts an axios error into a human-readable string.
 *
 * FastAPI returns two shapes for `detail`:
 *   - string  → simple message, e.g. "Email already registered"
 *   - array   → Pydantic 422 validation errors:
 *               [{ type, loc, msg, input, ctx, url }, ...]
 *
 * Treating the array as a string causes React to crash. This helper always
 * returns a plain string regardless of which shape the backend sends.
 */

import axios from 'axios';

interface PydanticError {
  msg?: string;
  loc?: (string | number)[];
}

export function parseApiError(err: unknown, fallback: string): string {
  if (!axios.isAxiosError(err)) return fallback;

  const detail = err.response?.data?.detail;

  // Array → Pydantic validation errors
  if (Array.isArray(detail)) {
    return detail
      .map((e: PydanticError) => {
        const field = e.loc ? e.loc.filter((s) => s !== 'body').join('.') : '';
        const msg = e.msg ?? 'Invalid value';
        return field ? `${field}: ${msg}` : msg;
      })
      .join(' · ') || fallback;
  }

  // Plain string
  if (typeof detail === 'string' && detail.trim()) return detail;

  return fallback;
}
