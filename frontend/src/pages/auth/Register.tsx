/**
 * Register.tsx
 * Public registration page — POST /api/auth/register
 * On success the account is active immediately (no email verification required).
 * We show a "Registration successful" screen and link the user to sign-in.
 */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { parseApiError } from '../../services/parseApiError';

// Per-country phone rules: min/max = local digit count (after stripping leading 0)
const COUNTRY_CODES = [
  { code: '+91',  flag: '🇮🇳', name: 'India',        min: 10, max: 10, placeholder: '9876543210'  },
  { code: '+1',   flag: '🇺🇸', name: 'USA / Canada', min: 10, max: 10, placeholder: '2025550123'  },
  { code: '+44',  flag: '🇬🇧', name: 'UK',           min: 10, max: 10, placeholder: '7911123456'  },
  { code: '+61',  flag: '🇦🇺', name: 'Australia',    min:  9, max:  9, placeholder: '412345678'   },
  { code: '+971', flag: '🇦🇪', name: 'UAE',          min:  9, max:  9, placeholder: '501234567'   },
  { code: '+966', flag: '🇸🇦', name: 'Saudi Arabia', min:  9, max:  9, placeholder: '512345678'   },
  { code: '+974', flag: '🇶🇦', name: 'Qatar',        min:  8, max:  8, placeholder: '33412345'    },
  { code: '+65',  flag: '🇸🇬', name: 'Singapore',    min:  8, max:  8, placeholder: '91234567'    },
  { code: '+60',  flag: '🇲🇾', name: 'Malaysia',     min:  9, max: 10, placeholder: '123456789'   },
  { code: '+49',  flag: '🇩🇪', name: 'Germany',      min:  6, max: 11, placeholder: '15123456789' },
  { code: '+33',  flag: '🇫🇷', name: 'France',       min:  9, max:  9, placeholder: '612345678'   },
  { code: '+39',  flag: '🇮🇹', name: 'Italy',        min:  9, max: 10, placeholder: '3123456789'  },
  { code: '+34',  flag: '🇪🇸', name: 'Spain',        min:  9, max:  9, placeholder: '612345678'   },
  { code: '+31',  flag: '🇳🇱', name: 'Netherlands',  min:  9, max:  9, placeholder: '612345678'   },
  { code: '+7',   flag: '🇷🇺', name: 'Russia',       min: 10, max: 10, placeholder: '9161234567'  },
  { code: '+86',  flag: '🇨🇳', name: 'China',        min: 11, max: 11, placeholder: '13123456789' },
  { code: '+81',  flag: '🇯🇵', name: 'Japan',        min: 10, max: 11, placeholder: '9012345678'  },
  { code: '+82',  flag: '🇰🇷', name: 'South Korea',  min: 10, max: 11, placeholder: '1012345678'  },
  { code: '+55',  flag: '🇧🇷', name: 'Brazil',       min: 10, max: 11, placeholder: '11912345678' },
  { code: '+52',  flag: '🇲🇽', name: 'Mexico',       min: 10, max: 10, placeholder: '5512345678'  },
  { code: '+27',  flag: '🇿🇦', name: 'South Africa', min:  9, max:  9, placeholder: '712345678'   },
  { code: '+20',  flag: '🇪🇬', name: 'Egypt',        min: 10, max: 10, placeholder: '1001234567'  },
  { code: '+234', flag: '🇳🇬', name: 'Nigeria',      min: 10, max: 10, placeholder: '8012345678'  },
  { code: '+254', flag: '🇰🇪', name: 'Kenya',        min:  9, max:  9, placeholder: '712345678'   },
  { code: '+92',  flag: '🇵🇰', name: 'Pakistan',     min: 10, max: 10, placeholder: '3001234567'  },
  { code: '+880', flag: '🇧🇩', name: 'Bangladesh',   min: 10, max: 10, placeholder: '1812345678'  },
  { code: '+94',  flag: '🇱🇰', name: 'Sri Lanka',    min:  9, max:  9, placeholder: '771234567'   },
  { code: '+977', flag: '🇳🇵', name: 'Nepal',        min:  9, max: 10, placeholder: '9841234567'  },
  { code: '+90',  flag: '🇹🇷', name: 'Turkey',       min: 10, max: 10, placeholder: '5301234567'  },
];

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

  // Current country rules derived from selected dial code
  const currentCountry = COUNTRY_CODES.find((c) => c.code === dialCode) ?? COUNTRY_CODES[0];
  const phoneHint =
    currentCountry.min === currentCountry.max
      ? `${currentCountry.min} digits`
      : `${currentCountry.min}–${currentCountry.max} digits`;

  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  // Digits-only, strip leading zeros for E.164
  const digits = localNumber.replace(/\D/g, '');
  const fullPhone = digits ? `${dialCode}${digits}` : '';

  const handlePhoneInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Strip any non-digit character as the user types
    const cleaned = e.target.value.replace(/\D/g, '');
    setLocalNumber(cleaned.slice(0, currentCountry.max));
  };

  const handleCountryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setDialCode(e.target.value);
    setLocalNumber(''); // reset number when country changes
  };

  const validate = (): string => {
    if (!form.name.trim() || form.name.trim().length < 2)
      return 'Name must be at least 2 characters.';
    if (!form.email) return 'Email is required.';
    if (digits.length > 0 && (digits.length < currentCountry.min || digits.length > currentCountry.max))
      return `Phone number for ${currentCountry.name} must be ${phoneHint}.`;
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
      await api.post('/api/auth/register', {
        name: form.name.trim(),
        email: form.email,
        phone_number: fullPhone || undefined,
        password: form.password,
      });

      // Navigate to login with a success flag — no intermediate blank screen
      navigate('/login', { state: { registered: true } });
    } catch (err: unknown) {
      const msg = parseApiError(err, 'Registration failed');
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

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
                onChange={handleCountryChange}
                className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-2 py-2 focus:outline-none focus:border-[#3B82F6] transition-colors cursor-pointer appearance-none"
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
                inputMode="numeric"
                value={localNumber}
                onChange={handlePhoneInput}
                maxLength={currentCountry.max}
                className={`flex-1 bg-[#0B0F19] border text-white text-sm rounded px-3 py-2 focus:outline-none transition-colors ${
                  localNumber && (digits.length < currentCountry.min || digits.length > currentCountry.max)
                    ? 'border-[#FF9500] focus:border-[#FF9500]'
                    : digits.length >= currentCountry.min
                    ? 'border-[#34C759]/50 focus:border-[#34C759]'
                    : 'border-[#1F2937] focus:border-[#3B82F6]'
                }`}
                placeholder={currentCountry.placeholder}
              />
            </div>
            {/* Live digit counter hint */}
            <div className="flex justify-between items-center">
              <span className="text-[#4B5563] text-[11px]">
                {currentCountry.flag} {currentCountry.name} — {phoneHint}
              </span>
              {localNumber && (
                <span
                  className="text-[11px] font-mono"
                  style={{
                    color:
                      digits.length >= currentCountry.min && digits.length <= currentCountry.max
                        ? '#34C759'
                        : '#FF9500',
                  }}
                >
                  {digits.length}/{currentCountry.max}
                </span>
              )}
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
