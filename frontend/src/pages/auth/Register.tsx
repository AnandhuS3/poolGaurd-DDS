/**
 * Register.tsx
 * Public registration page — POST /api/auth/register
 * On success (201 Created) the account is immediately active.
 * We show a "success" screen with a link to sign in.
 */

import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import api from '../../services/api';

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

// Maximum local subscriber digits (without country code or leading zeros) per dial code.
// Used both for input capping and validation.
const PHONE_MAX_DIGITS: Record<string, number> = {
  '+91':  10, // India
  '+1':   10, // USA / Canada
  '+44':  10, // UK
  '+61':   9, // Australia
  '+971':  9, // UAE
  '+966':  9, // Saudi Arabia
  '+974':  8, // Qatar
  '+65':   8, // Singapore
  '+60':  10, // Malaysia (up to 10)
  '+49':  11, // Germany (variable, up to 11)
  '+33':   9, // France
  '+39':  10, // Italy
  '+34':   9, // Spain
  '+31':   9, // Netherlands
  '+7':   10, // Russia
  '+86':  11, // China
  '+81':  10, // Japan
  '+82':  10, // South Korea
  '+55':  11, // Brazil (11 with mobile 9-prefix)
  '+52':  10, // Mexico
  '+27':   9, // South Africa
  '+20':  10, // Egypt
  '+234': 10, // Nigeria
  '+254':  9, // Kenya
  '+92':  10, // Pakistan
  '+880': 10, // Bangladesh
  '+94':   9, // Sri Lanka
  '+977': 10, // Nepal
  '+90':  10, // Turkey
};

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
  const [registered, setRegistered] = useState(false); // set after successful registration

  const strength = passwordStrength(form.password);

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  // Max digits allowed for the currently selected country
  const maxDigits = PHONE_MAX_DIGITS[dialCode] ?? 15;

  // Combine dial code + local number into E.164-style string
  const fullPhone = localNumber.trim()
    ? `${dialCode}${localNumber.replace(/^0+/, '').replace(/\s/g, '')}`
    : '';

  const validate = (): string => {
    if (!form.name.trim() || form.name.trim().length < 2)
      return 'Name must be at least 2 characters.';
    if (!form.email) return 'Email is required.';
    if (form.password.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Z]/.test(form.password)) return 'Password must contain at least one uppercase letter.';
    if (!/[0-9]/.test(form.password)) return 'Password must contain at least one digit.';
    if (form.password !== form.confirm) return 'Passwords do not match.';
    if (localNumber.trim()) {
      const digits = localNumber.replace(/\D/g, '');
      if (digits.length !== maxDigits)
        return `Phone number must be exactly ${maxDigits} digits for ${dialCode}.`;
    }
    return '';
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    const validationError = validate();
    if (validationError) { setError(validationError); return; }

    setIsLoading(true);
    try {
      await api.post('/api/auth/register', {
        name: form.name.trim(),
        email: form.email,
        phone_number: fullPhone || undefined,
        password: form.password,
      });

      // 201 Created — account is immediately active
      setRegistered(true);
    } catch (err: unknown) {
      const msg = axios.isAxiosError(err)
        ? (err.response?.data?.detail as string) ?? 'Registration failed'
        : 'Registration failed';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // -----------------------------------------------------------------------
  // Success screen — account is immediately active, direct user to login
  // -----------------------------------------------------------------------
  if (registered) {
    return (
      <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-4">
        <div className="w-full max-w-sm text-center space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-widest uppercase">PoolGuard</h1>
            <p className="text-[#9CA3AF] text-sm mt-1">Drowning Detection System</p>
          </div>

          <div className="bg-[#121212] border border-[#1F2937] rounded p-8 flex flex-col items-center gap-4">
            <div className="text-5xl">✅</div>
            <h2 className="text-white font-semibold text-lg">Account Created!</h2>
            <p className="text-[#9CA3AF] text-sm leading-relaxed">
              Your account has been created successfully.<br />
              You can sign in right away.
            </p>
            <Link
              to="/login"
              className="mt-2 w-full bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-semibold py-2.5 rounded transition-colors text-center"
            >
              Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Registration form
  // -----------------------------------------------------------------------
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

          {/* Phone (optional) */}
          <div className="flex flex-col gap-1.5">
            <label className="text-[#9CA3AF] text-xs uppercase tracking-wide">
              Phone Number <span className="text-[#4B5563] normal-case">(optional)</span>
            </label>
            <div className="flex gap-2">
              <select
                value={dialCode}
                onChange={(e) => { setDialCode(e.target.value); setLocalNumber(''); }}
                className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-2 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors cursor-pointer appearance-none pr-6"
                style={{ minWidth: '5.5rem', backgroundImage: 'none' }}
              >
                {COUNTRY_CODES.map(({ code, flag, name }) => (
                  <option key={code + name} value={code}>
                    {flag} {code} ({name})
                  </option>
                ))}
              </select>
              <input
                type="tel"
                value={localNumber}
                onChange={(e) => {
                  // Allow only digits, strip leading zeros, cap at country max
                  const digits = e.target.value.replace(/\D/g, '').slice(0, maxDigits);
                  setLocalNumber(digits);
                }}
                maxLength={maxDigits}
                inputMode="numeric"
                className="flex-1 bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors"
                placeholder={`${'0'.repeat(maxDigits)} (${maxDigits} digits)`}
              />
            </div>
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
