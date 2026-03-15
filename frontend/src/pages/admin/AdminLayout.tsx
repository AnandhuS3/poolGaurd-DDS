/**
 * AdminLayout.tsx
 * Wrapper for all /admin/* routes.
 * Enforces admin-only access: redirects non-admins to /.
 * Provides a sidebar nav for admin sub-pages.
 */

import { Navigate, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const ADMIN_LINKS = [
  { to: '/admin', label: 'Dashboard', end: true },
  { to: '/admin/cctv-manager', label: 'CCTV Manager' },
  { to: '/admin/guard-monitor', label: '📱 Guard Monitor' },
  { to: '/admin/users', label: 'User Management' },
  { to: '/admin/system-admin', label: 'System Admin' },
  { to: '/admin/sessions', label: 'Active Sessions' },
  { to: '/admin/alerts', label: 'Alert History' },
];

export function AdminLayout() {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;
  if (!user || user.role !== 'admin') return <Navigate to="/" replace />;

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar */}
      <aside className="w-48 shrink-0 bg-[#0D1117] border-r border-[#1F2937] flex flex-col py-4 gap-1 overflow-y-auto">
        <p className="px-4 text-[10px] uppercase tracking-widest text-[#4B5563] font-semibold mb-2">
          Admin Panel
        </p>
        {ADMIN_LINKS.map(({ to, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `mx-2 px-3 py-2 rounded text-xs font-medium transition-colors ${
                isActive
                  ? 'bg-[#1F2937] text-white'
                  : 'text-[#9CA3AF] hover:text-white hover:bg-[#1A1A1A]'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </aside>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  );
}
