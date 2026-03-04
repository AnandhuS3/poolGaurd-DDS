/**
 * Navbar.tsx
 * Top navigation bar. Professional surveillance dashboard style.
 */

import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../core/websocket/useWebSocket';

const WS_STATUS_COLORS: Record<string, string> = {
  connected: '#34C759',
  connecting: '#FF9500',
  reconnecting: '#FF9500',
  disconnected: '#FF3B30',
  error: '#FF3B30',
  idle: '#6B7280',
};

export function Navbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { status } = useWebSocket();

  const dot = WS_STATUS_COLORS[status] ?? '#6B7280';
  const isAdmin = user?.role === 'admin';

  const navLinks = [
    { to: '/', label: 'Dashboard' },
    { to: '/upload', label: 'Upload' },
    { to: '/live', label: 'Live Feed' },
    ...(isAdmin ? [{ to: '/admin', label: 'Admin' }] : []),
  ];

  return (
    <header className="h-12 flex items-center justify-between px-5 bg-[#121212] border-b border-[#1F2937] shrink-0 z-20">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <span className="font-bold text-white tracking-widest text-sm uppercase">
          PoolGuard
        </span>
        <span className="text-[#374151] text-xs select-none">DDS v2</span>
      </div>

      {/* Navigation */}
      <nav className="flex items-center gap-1">
        {navLinks.map(({ to, label }) => {
          const active =
            to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(to);
          return (
            <Link
              key={to}
              to={to}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                active
                  ? 'bg-[#1F2937] text-white'
                  : 'text-[#9CA3AF] hover:text-white hover:bg-[#1A1A1A]'
              }`}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Right side: WS status + user */}
      <div className="flex items-center gap-4 text-xs">
        {/* WebSocket indicator */}
        <div className="flex items-center gap-1.5 text-[#9CA3AF]">
          <span
            className="w-2 h-2 rounded-full inline-block"
            style={{ backgroundColor: dot }}
          />
          <span className="uppercase tracking-wide">{status}</span>
        </div>

        {/* User */}
        {user && (
          <div className="flex items-center gap-2 text-[#9CA3AF]">
            <Link
              to="/profile"
              className="hover:text-white transition-colors"
              title="My Profile"
            >
              {user.name?.trim() || user.email || 'User'}
            </Link>
            <span className="text-[#4B5563]">·</span>
            <span className="uppercase text-[10px] text-[#6B7280]">{user.role}</span>
            <span className="text-[#374151] text-[10px] font-mono">#{user.id}</span>
            <button
              onClick={logout}
              className="ml-1 text-[#6B7280] hover:text-white transition-colors"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
