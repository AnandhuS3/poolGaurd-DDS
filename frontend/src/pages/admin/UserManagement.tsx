/**
 * UserManagement.tsx
 * Full CRUD for users — Admin only.
 *
 * GET    /api/admin/users
 * POST   /api/admin/users
 * PATCH  /api/admin/users/{id}
 * DELETE /api/admin/users/{id}
 */

import { useEffect, useState, type FormEvent } from 'react';
import axios from 'axios';
import { parseApiError } from '../../services/parseApiError';
import api from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface AdminUser {
  id: number;
  name: string;
  email: string;
  phone_number?: string;
  role: 'admin' | 'guard';
  is_active: boolean;
}

type ModalMode = 'create' | 'edit' | null;

const emptyForm = {
  name: '',
  email: '',
  phone_number: '',
  password: '',
  role: 'guard' as 'admin' | 'guard',
};

export function UserManagement() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [editTarget, setEditTarget] = useState<AdminUser | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState('');
  const [formLoading, setFormLoading] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    setListError('');
    try {
      const res = await api.get<AdminUser[]>('/api/admin/users');
      setUsers(res.data);
    } catch {
      setListError('Failed to load users.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const openCreate = () => {
    setForm(emptyForm);
    setFormError('');
    setEditTarget(null);
    setModalMode('create');
  };

  const openEdit = (u: AdminUser) => {
    setForm({
      name: u.name,
      email: u.email,
      phone_number: u.phone_number ?? '',
      password: '',
      role: u.role,
    });
    setFormError('');
    setEditTarget(u);
    setModalMode('edit');
  };

  const closeModal = () => { setModalMode(null); setEditTarget(null); };

  const set = (field: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFormLoading(true);
    try {
      if (modalMode === 'create') {
        await api.post('/api/admin/users', {
          name: form.name.trim(),
          email: form.email,
          phone_number: form.phone_number,
          password: form.password,
          role: form.role,
        });
      } else if (modalMode === 'edit' && editTarget) {
        const payload: Record<string, unknown> = {
          name: form.name.trim(),
          email: form.email,
          phone_number: form.phone_number || undefined,
          role: form.role,
        };
        if (form.password) payload.password = form.password;
        await api.patch(`/api/admin/users/${editTarget.id}`, payload);
      }
      closeModal();
      await fetchUsers();
    } catch (err: unknown) {
      setFormError(
        axios.isAxiosError(err)
          ? parseApiError(err, 'Operation failed')
          : 'Operation failed',
      );
    } finally {
      setFormLoading(false);
    }
  };

  const toggleActive = async (u: AdminUser) => {
    try {
      await api.patch(`/api/admin/users/${u.id}`, { is_active: !u.is_active });
      await fetchUsers();
    } catch {
      /* ignore */
    }
  };

  const deleteUser = async (u: AdminUser) => {
    if (!confirm(`Delete user "${u.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/api/admin/users/${u.id}`);
      await fetchUsers();
    } catch (err: unknown) {
      alert(
        axios.isAxiosError(err)
          ? parseApiError(err, 'Delete failed')
          : 'Delete failed',
      );
    }
  };

  return (
    <div className="p-6 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-white font-semibold text-base">User Management</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">Create, edit, and deactivate users.</p>
        </div>
        <button
          onClick={openCreate}
          className="px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-xs font-semibold rounded transition-colors"
        >
          + New User
        </button>
      </div>

      {/* Table */}
      <div className="bg-[#121212] border border-[#1F2937] rounded overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-[#9CA3AF] text-sm">Loading…</div>
        ) : listError ? (
          <div className="p-8 text-center text-[#FF3B30] text-sm">{listError}</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1F2937]">
                {['Name', 'Email', 'Phone', 'Role', 'Status', 'Actions'].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-[#9CA3AF] text-xs uppercase tracking-wide font-medium"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-[#6B7280]">
                    No users found.
                  </td>
                </tr>
              )}
              {users.map((u) => (
                <tr key={u.id} className="border-b border-[#1A1A1A] hover:bg-[#0F1318] transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{u.name}</td>
                  <td className="px-4 py-3 text-[#9CA3AF]">{u.email}</td>
                  <td className="px-4 py-3 text-[#9CA3AF]">{u.phone_number ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-[#1F2937] text-[#9CA3AF] text-[11px] rounded uppercase tracking-wide">
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                        u.is_active
                          ? 'bg-[#34C759]/10 text-[#34C759]'
                          : 'bg-[#FF3B30]/10 text-[#FF3B30]'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openEdit(u)}
                        className="text-[#9CA3AF] hover:text-white text-xs transition-colors"
                      >
                        Edit
                      </button>
                      {u.id !== me?.id && (
                        <>
                          <span className="text-[#374151]">·</span>
                          <button
                            onClick={() => toggleActive(u)}
                            className="text-[#9CA3AF] hover:text-white text-xs transition-colors"
                          >
                            {u.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                          <span className="text-[#374151]">·</span>
                          <button
                            onClick={() => deleteUser(u)}
                            className="text-[#FF3B30] hover:text-red-400 text-xs transition-colors"
                          >
                            Delete
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal */}
      {modalMode && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[#121212] border border-[#1F2937] rounded w-full max-w-sm p-6 flex flex-col gap-4">
            <h2 className="text-white font-semibold text-sm uppercase tracking-wide">
              {modalMode === 'create' ? 'Create User' : 'Edit User'}
            </h2>

            {formError && (
              <div className="bg-[#FF3B30]/10 border border-[#FF3B30]/40 text-[#FF3B30] text-xs rounded p-3">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-[#9CA3AF] text-xs">Full Name</label>
                <input
                  required
                  value={form.name}
                  onChange={set('name')}
                  className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[#9CA3AF] text-xs">Email</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={set('email')}
                  className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[#9CA3AF] text-xs">Phone (with country code)</label>
                <input
                  type="tel"
                  value={form.phone_number}
                  onChange={set('phone_number')}
                  required={modalMode === 'create'}
                  className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
                  placeholder="+91 9876543210"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[#9CA3AF] text-xs">
                  Password{modalMode === 'edit' && ' (leave blank to keep)'}
                </label>
                <input
                  type="password"
                  required={modalMode === 'create'}
                  value={form.password}
                  onChange={set('password')}
                  className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
                  placeholder={modalMode === 'edit' ? 'Leave blank to keep current' : 'Min 8 chars, 1 uppercase, 1 digit'}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[#9CA3AF] text-xs">Role</label>
                <select
                  value={form.role}
                  onChange={set('role')}
                  className="bg-[#0B0F19] border border-[#1F2937] text-white text-sm rounded px-3 py-2 focus:outline-none focus:border-[#3B82F6]"
                >
                  <option value="guard">Guard</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={formLoading}
                  className="flex-1 py-2 bg-[#3B82F6] hover:bg-[#2563EB] disabled:opacity-50 text-white text-xs font-semibold rounded transition-colors"
                >
                  {formLoading ? 'Saving…' : modalMode === 'create' ? 'Create' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={closeModal}
                  className="flex-1 py-2 bg-[#1F2937] hover:bg-[#374151] text-[#9CA3AF] text-xs rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
