/**
 * App.tsx
 * Root component. Sets up routing and global layout.
 *
 * Layout:
 *   [Navbar]
 *   [Route content – flex-1 overflow]
 *   [StatusBar]
 *
 * Auth guard: Redirects to /login if not authenticated.
 * Admin guard (inside AdminLayout): Redirects to / if role !== 'admin'.
 */

import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/layout/Navbar';
import { StatusBar } from './components/layout/StatusBar';
import { Dashboard } from './pages/Dashboard';
import { Upload } from './pages/Upload';
import { Live } from './pages/Live';
import { Login } from './pages/Login';
import { Register } from './pages/auth/Register';
import { Profile } from './pages/profile/Profile';
import { ChangePassword } from './pages/profile/ChangePassword';
import { AdminLayout } from './pages/admin/AdminLayout';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { UserManagement } from './pages/admin/UserManagement';
import { SystemAdmin } from './pages/admin/SystemAdmin';
import { Sessions } from './pages/admin/Sessions';
import { AlertHistory } from './pages/admin/AlertHistory';

// Auth guard wrapper — waits for /me check before deciding
function ProtectedLayout() {
  const { token, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center">
        <span className="text-[#6B7280] text-sm">Loading…</span>
      </div>
    );
  }
  if (!token) return <Navigate to="/login" replace />;
  return (
    <div className="flex flex-col h-full bg-[#0B0F19]">
      <Navbar />
      <main className="flex-1 flex overflow-hidden relative">
        <Outlet />
      </main>
      <StatusBar />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected routes */}
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/live" element={<Live />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/profile/change-password" element={<ChangePassword />} />

            {/* Admin sub-routes — AdminLayout enforces role check */}
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<AdminDashboard />} />
              <Route path="users" element={<UserManagement />} />
              <Route path="system-admin" element={<SystemAdmin />} />
              <Route path="sessions" element={<Sessions />} />
              <Route path="alerts" element={<AlertHistory />} />
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
