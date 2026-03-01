/**
 * AlertHistory.tsx
 * Paginated alert history — Admin only.
 * GET /api/admin/alerts?limit=100
 */

import { useEffect, useState } from 'react';
import api from '../../services/api';

interface AlertRecord {
  id: number;
  person_id?: number;
  alert_type?: string;
  severity?: string;
  message?: string;
  timestamp?: string;
  created_at?: string;
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

  useEffect(() => {
    setIsLoading(true);
    setError('');
    api
      .get<AlertRecord[]>('/api/admin/alerts?limit=1000')
      .then((r) => setAlerts(r.data ?? []))
      .catch(() => setError('Failed to load alert history.'))
      .finally(() => setIsLoading(false));
  }, []);

  const totalPages = Math.max(1, Math.ceil(alerts.length / PAGE_SIZE));
  const pageAlerts = alerts.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-white font-semibold text-base">Alert History</h1>
        <p className="text-[#9CA3AF] text-sm mt-0.5">All drowning/detection alerts recorded by the system.</p>
      </div>

      {/* Count */}
      {!isLoading && !error && (
        <p className="text-[#4B5563] text-xs">
          Total: <span className="text-[#9CA3AF]">{alerts.length}</span> alerts
        </p>
      )}

      <div className="bg-[#121212] border border-[#1F2937] rounded overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-[#9CA3AF] text-sm">Loading…</div>
        ) : error ? (
          <div className="p-8 text-center text-[#FF3B30] text-sm">{error}</div>
        ) : alerts.length === 0 ? (
          <div className="p-8 text-center text-[#6B7280] text-sm">No alerts recorded yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1F2937]">
                {['ID', 'Type', 'Severity', 'Message', 'Timestamp', 'Video'].map((h) => (
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
                const ts = a.timestamp ?? a.created_at;
                const sev = (a.severity ?? 'info').toLowerCase();
                return (
                  <tr key={a.id} className="border-b border-[#1A1A1A] hover:bg-[#0F1318] transition-colors">
                    <td className="px-4 py-3 text-[#6B7280] font-mono text-xs">{a.id}</td>
                    <td className="px-4 py-3 text-[#9CA3AF]">{a.alert_type ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                          SEVERITY_COLORS[sev] ?? 'bg-[#1F2937] text-[#9CA3AF]'
                        }`}
                      >
                        {sev.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#9CA3AF] max-w-xs truncate">{a.message ?? '—'}</td>
                    <td className="px-4 py-3 text-[#9CA3AF] font-mono text-xs whitespace-nowrap">
                      {ts ? new Date(ts).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-[#9CA3AF] text-xs truncate max-w-[120px]">
                      {a.video_file ?? '—'}
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
