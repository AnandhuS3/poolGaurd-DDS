/**
 * AlertHistory.tsx
 * Paginated alert history with Resolve action — Admin only.
 * GET /api/admin/alerts?limit=1000
 * POST /api/alerts/{id}/acknowledge  ← resolve
 */

import { useEffect, useState } from 'react';
import api from '../../services/api';
import { parseApiError } from '../../services/parseApiError';

interface AlertRecord {
  id: number;
  person_id?: number;
  alert_type?: string;
  track_id?: number;
  camera_name?: string;
  severity?: string;
  message?: string;
  timestamp?: string;
  triggered_at?: string;
  created_at?: string;
  resolved_at?: string | null;
  video_file?: string;
}

const PAGE_SIZE = 20;

const SEVERITY_COLORS: Record<string, string> = {
  danger: 'bg-[#FF3B30]/10 text-[#FF3B30]',
  warning: 'bg-[#FF9500]/10 text-[#FF9500]',
  info: 'bg-[#3B82F6]/10 text-[#3B82F6]',
};

export function AlertHistory() {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [filter, setFilter] = useState<'all' | 'open' | 'resolved'>('all');
  const [selectedAlerts, setSelectedAlerts] = useState<Set<number>>(new Set());

  const fetchAlerts = async () => {
    setIsLoading(true);
    setError('');
    api
      .get<AlertRecord[]>('/api/admin/alerts?limit=1000')
      .then((r) => setAlerts(r.data ?? []))
      .catch(() => setError('Failed to load alert history.'))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const handleResolve = async (id: number) => {
    if (!window.confirm(`Mark Alert #${id} as resolved? This will remove it from all guards' mobile screens.`)) return;
    setResolvingId(id);
    try {
      await api.post(`/api/alerts/${id}/acknowledge`);
      // Update locally for instant feedback
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === id ? { ...a, resolved_at: new Date().toISOString() } : a
        )
      );
    } catch (err) {
      alert(parseApiError(err, 'Failed to resolve alert'));
    } finally {
      setResolvingId(null);
    }
  };

  const filtered = alerts.filter((a) => {
    if (filter === 'open') return !a.resolved_at;
    if (filter === 'resolved') return !!a.resolved_at;
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageAlerts = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const openCount = alerts.filter((a) => !a.resolved_at).length;
  const resolvedCount = alerts.filter((a) => !!a.resolved_at).length;

  const handleClearSelected = async () => {
    if (selectedAlerts.size === 0) return;
    if (!window.confirm(`Are you sure you want to permanently delete ${selectedAlerts.size} selected alert(s)?`)) return;
    try {
      await api.delete("/api/admin/alerts", { data: { alert_ids: Array.from(selectedAlerts) } });
      setAlerts(prev => prev.filter(a => !selectedAlerts.has(a.id)));
      setSelectedAlerts(new Set());
    } catch (err) {
      alert(parseApiError(err, 'Failed to clear alerts'));
    }
  };

  const toggleSelection = (id: number) => {
    const newSelection = new Set(selectedAlerts);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedAlerts(newSelection);
  };

  const toggleAll = (visibleIds: number[]) => {
    const allSelected = visibleIds.every(id => selectedAlerts.has(id));
    const newSelection = new Set(selectedAlerts);
    if (allSelected) {
      visibleIds.forEach(id => newSelection.delete(id));
    } else {
      visibleIds.forEach(id => newSelection.add(id));
    }
    setSelectedAlerts(newSelection);
  };

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-white font-semibold text-base">Alert History</h1>
          <p className="text-[#9CA3AF] text-sm mt-0.5">All drowning/detection alerts recorded by the system.</p>
        </div>
        <div className="flex items-center gap-3">
          {selectedAlerts.size > 0 && (
            <button
               onClick={handleClearSelected}
               className="px-3 py-1.5 bg-[#EF4444] hover:bg-[#DC2626] text-white text-xs rounded transition-colors"
            >
              Clear Selected ({selectedAlerts.size})
            </button>
          )}
          <button
            onClick={fetchAlerts}
            className="px-3 py-1.5 bg-[#1F2937] hover:bg-[#374151] text-[#9CA3AF] hover:text-white text-xs rounded transition-colors"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Stats + filter */}
      {!isLoading && !error && (
        <div className="flex items-center gap-3 flex-wrap">
          {[
            { key: 'all', label: `All (${alerts.length})` },
            { key: 'open', label: `🚨 Unresolved (${openCount})` },
            { key: 'resolved', label: `✅ Resolved (${resolvedCount})` },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => { setFilter(key as typeof filter); setPage(0); }}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                filter === key
                  ? 'bg-[#3B82F6] text-white'
                  : 'bg-[#1F2937] text-[#9CA3AF] hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      <div className="bg-[#121212] border border-[#1F2937] rounded overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-[#9CA3AF] text-sm">Loading…</div>
        ) : error ? (
          <div className="p-8 text-center text-[#FF3B30] text-sm">{error}</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-[#6B7280] text-sm">No alerts in this category.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1F2937]">
                <th className="px-4 py-3 text-left w-10">
                  <input
                    type="checkbox"
                    checked={pageAlerts.length > 0 && pageAlerts.every(a => selectedAlerts.has(a.id))}
                    onChange={() => toggleAll(pageAlerts.map(a => a.id))}
                    className="rounded border-[#374151] bg-[#1F2937] text-[#3B82F6] focus:ring-[#3B82F6] cursor-pointer"
                  />
                </th>
                {['ID', 'Type', 'Camera', 'Track', 'Severity', 'Timestamp', 'Status', 'Action'].map((h) => (
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
              {pageAlerts.map((a) => {
                const ts = a.timestamp ?? a.triggered_at ?? a.created_at;
                const sev = (a.alert_type ?? 'info').toLowerCase();
                const isResolved = !!a.resolved_at;
                const isSelected = selectedAlerts.has(a.id);
                return (
                  <tr
                    key={a.id}
                    className={`border-b border-[#1A1A1A] transition-colors ${
                      isSelected ? 'bg-[#3B82F6]/10' :
                      isResolved ? 'opacity-50 hover:opacity-70' : 'hover:bg-[#0F1318]'
                    }`}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          // Prevent triggering row clicks if any in future
                          e.stopPropagation();
                          toggleSelection(a.id);
                        }}
                        className="rounded border-[#374151] bg-[#1F2937] text-[#3B82F6] focus:ring-[#3B82F6] cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-3 text-[#6B7280] font-mono text-xs">#{a.id}</td>
                    <td className="px-4 py-3 text-[#9CA3AF]">{a.alert_type ?? '—'}</td>
                    <td className="px-4 py-3 text-[#9CA3AF] text-xs">{a.camera_name ?? '—'}</td>
                    <td className="px-4 py-3 text-[#9CA3AF] font-mono text-xs">{a.track_id ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                          SEVERITY_COLORS[sev] ?? 'bg-[#1F2937] text-[#9CA3AF]'
                        }`}
                      >
                        {sev.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#9CA3AF] font-mono text-xs whitespace-nowrap">
                      {ts ? new Date(ts).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {isResolved ? (
                        <span className="text-[#10B981] text-xs">✅ Resolved</span>
                      ) : (
                        <span className="text-[#EF4444] text-xs">🔴 Open</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {!isResolved && (
                        <button
                          onClick={() => handleResolve(a.id)}
                          disabled={resolvingId === a.id}
                          className="text-xs text-[#10B981] hover:text-[#059669] disabled:opacity-50 font-medium"
                        >
                          {resolvingId === a.id ? 'Resolving…' : 'Resolve'}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {!isLoading && !error && totalPages > 1 && (
        <div className="flex items-center gap-2 justify-end">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 bg-[#1F2937] hover:bg-[#374151] disabled:opacity-40 text-[#9CA3AF] text-xs rounded transition-colors"
          >
            ← Prev
          </button>
          <span className="text-[#6B7280] text-xs">
            Page {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1.5 bg-[#1F2937] hover:bg-[#374151] disabled:opacity-40 text-[#9CA3AF] text-xs rounded transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
