/**
 * Register.tsx
 * Public registration page — POST /api/auth/register
 * On success the backend auto-logs in; we store the token and redirect.
 */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import type { AuthTokens } from '../../types/detection';

// Common country dial codes — flag emoji + dial code + country name
const COUNTRY_CODES = [
  { code: '+91',  flag: '🇮🇳', name: 'India' },
  { code: '+1',   flag: '🇺🇸', name: 'USA / Canada' },
  { code: '+44',  flag: '🇬🇧', name: 'UK' },
  { code: '+61',  flag: '🇦🇺', name: 'Australia' },
  { code: '+971', flag: '🇦🇪', name: 'UAE' },
  { code: '+966', flag: '🇸🇦', name: 'Saudi Arabia' },
  { code: '+974', flag: '🇶🇦', name: 'Qatar' },
  { code: '+65',  flag: '🇸🇬', name: 'Singapore' },
  { code: '+60',  flag: '🇲🇾', name: 'Malaysia' },
  { code: '+49',  flag: '🇩🇪', name: 'Germany' },
  { code: '+33',  flag: '🇫🇷', name: 'France' },
  { code: '+39',  flag: '🇮🇹', name: 'Italy' },
  { code: '+34',  flag: '🇪🇸', name: 'Spain' },
  { code: '+31',  flag: '🇳🇱', name: 'Netherlands' },
  { code: '+7',   flag: '🇷🇺', name: 'Russia' },
  { code: '+86',  flag: '🇨🇳', name: 'China' },
  { code: '+81',  flag: '🇯🇵', name: 'Japan' },
  { code: '+82',  flag: '🇰🇷', name: 'South Korea' },
  { code: '+55',  flag: '🇧🇷', name: 'Brazil' },
  { code: '+52',  flag: '🇲🇽', name: 'Mexico' },
  { code: '+27',  flag: '🇿🇦', name: 'South Africa' },
  { code: '+20',  flag: '🇪🇬', name: 'Egypt' },
  { code: '+234', flag: '🇳🇬', name: 'Nigeria' },
  { code: '+254', flag: '🇰🇪', name: 'Kenya' },
  { code: '+92',  flag: '🇵🇰', name: 'Pakistan' },
  { code: '+880', flag: '🇧🇩', name: 'Bangladesh' },
  { code: '+94',  flag: '🇱🇰', name: 'Sri Lanka' },
  { code: '+977', flag: '🇳🇵', name: 'Nepal' },
  { code: '+90',  flag: '🇹🇷', name: 'Turkey' },
] as const;

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

export function Register() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirm: '',
  });
  const [dialCode, setDialCode] = useState('+91');
  const [localNumber, setLocalNumber] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const strength = passwordStrength(form.password);

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  // Combine dial code + local number into E.164-style string
  const fullPhone = `${dialCode}${localNumber.replace(/^0+/, '').replace(/\s/g, '')}`;

  const validate = (): string => {
    if (!form.name.trim() || form.name.trim().length < 2)
      return 'Name must be at least 2 characters.';
    if (!form.email) return 'Email is required.';
    if (!localNumber.trim() || localNumber.replace(/\D/g, '').length < 5)
      return 'Please enter a valid phone number.';
    if (form.password.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Z]/.test(form.password)) return 'Password must contain at least one uppercase letter.';
    if (!/[0-9]/.test(form.password)) return 'Password must contain at least one digit.';
    if (form.password !== form.confirm) return 'Passwords do not match.';
    return '';
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setIsLoading(true);
    try {
      // Register — backend auto-logs in and returns tokens
      const res = await api.post<AuthTokens>('/api/auth/register', {
        name: form.name.trim(),
        email: form.email,
        phone_number: fullPhone,
        password: form.password,
      });

      // Store token directly (backend already created a session)
      const { access_token } = res.data;
      localStorage.setItem('dds_token', access_token);
      localStorage.setItem('dds_user', JSON.stringify(res.data.user));

      // Use the login fn from context to hydrate state
      await login(form.email, form.password);
      navigate('/');
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail as string) ?? 'Registration failed'
        : 'Registration failed';
      setError(msg);
    } finally {
      setIsLoading(false);
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

        <form
          onSubmit={handleSubmit}
          className="bg-[#121212] border border-[#1F2937] rounded p-6 flex flex-col gap-4"
        >
          <h2 className="text-white font-semibold text-sm uppercase tracking-wide">Create Account</h2>

          {error && (
            <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/40 text-[#FF3B30] text-xs rounded p-3">
              {error}
            </div>
          )}

          {/* Full Name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Full Name</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={set('name')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="John Doe"
            />
          </div>

          {/* Email */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Email</label>
            <input
              type="email"
              required
              value={form.email}
              onChange={set('email')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="you@example.com"
            />
          </div>

          {/* Phone */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Phone Number</label>
            <div className="flex gap-2">
              {/* Country code dropdown */}
              <select
                value={dialCode}
                onChange={(e) => setDialCode(e.target.value)}
                className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-2 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors cursor-pointer appearance-none pr-6"
                style={{ minWidth: '5.5rem', backgroundImage: 'none' }}
              >
                {COUNTRY_CODES.map(({ code, flag, name }) => (
                  <option key={code + name} value={code}>
                    {flag} {code} ({name})
                  </option>
                ))}
              </select>
              {/* Local number input */}
              <input
                type="tel"
                required
                value={localNumber}
                onChange={(e) => setLocalNumber(e.target.value)}
                className="flex-1 bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
                placeholder="9876543210"
              />
            </div>
            <span className="text-[#4B5563] text-[11px]">
              Selected: {dialCode} — number will be sent as <span className="text-[#6B7280]">{fullPhone || dialCode + '…'}</span>
            </span>
          </div>

          {/* Password */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Password</label>
            <input
              type="password"
              required
              value={form.password}
              onChange={set('password')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="Min 8 chars, 1 uppercase, 1 digit"
            />
            {form.password && (
              <div className="flex flex-col gap-1 mt-1">
                <div className="h-1 bg-[#1F2937] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${(strength.score / 4) * 100}%`,
                      backgroundColor: strength.color,
                    }}
                  />
                </div>
                <span className="text-[11px]" style={{ color: strength.color }}>
                  {strength.label}
                </span>
              </div>
            )}
          </div>

          {/* Confirm Password */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">Confirm Password</label>
            <input
              type="password"
              required
              value={form.confirm}
              onChange={set('confirm')}
              className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="mt-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold py-2.5 rounded transition-colors"
          >
            {isLoading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>

        <p className="text-center text-[#6B7280] text-xs mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-[#3B82F6] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
