'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { Card, Loader, ErrorState, Input, Select } from '@/components/UI';
import type { RequestLog } from '@/lib/api';

export default function LogsPage() {
  const { token, apiKey } = useAuth();
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch('https://saki-gateway.indevs.in/admin/logs?limit=200', { headers });
      if (!r.ok) throw new Error(`${r.status}`);
      setLogs(await r.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, apiKey]);

  if (loading) return <Loader label="Loading logs" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  const filtered = logs.filter((l) => {
    if (statusFilter === 'ok' && l.status_code >= 400) return false;
    if (statusFilter === 'err' && l.status_code < 400) return false;
    if (filter) {
      const q = filter.toLowerCase();
      return (
        l.model.toLowerCase().includes(q) ||
        (l.provider || '').toLowerCase().includes(q) ||
        (l.error || '').toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 06 / Request logs</div>
          <h1 className="section-title">Traffic</h1>
          <p className="section-sub mono">
            {logs.length} entries · {logs.filter((l) => l.status_code >= 400).length} errors
          </p>
        </div>
        <div className="row">
          <Input value={filter} onChange={setFilter} placeholder="Filter model / error…" />
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'all', label: 'All' },
              { value: 'ok', label: 'OK only' },
              { value: 'err', label: 'Errors only' },
            ]}
          />
        </div>
      </header>

      <Card>
        {filtered.length === 0 ? (
          <div className="empty-box">No log entries.</div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Provider</th>
                  <th>Model</th>
                  <th>Tokens</th>
                  <th>Latency</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => (
                  <tr key={l.id}>
                    <td className="mono text-xs dim">{(l.created_at || '').replace('T', ' ').slice(0, 19)}</td>
                    <td className="mono text-sm">{l.provider || '—'}</td>
                    <td className="mono text-sm wrap" style={{ maxWidth: '14rem' }}>
                      {l.model}
                    </td>
                    <td className="mono text-xs">
                      {(l.input_tokens || 0).toLocaleString()} ↑ / {(l.output_tokens || 0).toLocaleString()} ↓
                    </td>
                    <td className="mono text-xs">{Math.round(l.latency_ms || 0)}ms</td>
                    <td>
                      {l.status_code >= 400 ? (
                        <span title={l.error || ''} className="badge badge-err">
                          {l.status_code}
                        </span>
                      ) : (
                        <span className="badge badge-ok">{l.status_code}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
