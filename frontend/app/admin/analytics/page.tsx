'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/api';
import { Card, Loader, ErrorState, Select, Stat } from '@/components/UI';
import type { RequestLog } from '@/lib/api';

type Analytics = {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
  error_count: number;
};

export default function AnalyticsPage() {
  const { token, apiKey } = useAuth();
  const [stats, setStats] = useState<Analytics | null>(null);
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState('7');

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [s, l] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/analytics?days=${days}`, { headers }).then((r) => {
          if (!r.ok) throw new Error(`${r.status}`);
          return r.json();
        }),
        fetch(`${API_BASE_URL}/admin/logs?limit=500`, { headers }).then((r) => (r.ok ? r.json() : [])),
      ]);
      setStats(s);
      setLogs(l);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days, token, apiKey]);

  if (loading) return <Loader label="Loading analytics" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  // Build a per-day request histogram from logs (last N days)
  const dayBuckets: Record<string, { count: number; errors: number }> = {};
  for (let i = parseInt(days) - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    dayBuckets[key] = { count: 0, errors: 0 };
  }
  for (const l of logs) {
    if (!l.created_at) continue;
    const day = l.created_at.slice(0, 10);
    if (day in dayBuckets) {
      dayBuckets[day].count++;
      if (l.status_code >= 400) dayBuckets[day].errors++;
    }
  }
  const maxCount = Math.max(1, ...Object.values(dayBuckets).map((b) => b.count));

  // Per-model aggregation
  const perModel: Record<string, { requests: number; errors: number; tokens: number }> = {};
  for (const l of logs) {
    const m = l.model || 'unknown';
    if (!perModel[m]) perModel[m] = { requests: 0, errors: 0, tokens: 0 };
    perModel[m].requests++;
    if (l.status_code >= 400) perModel[m].errors++;
    perModel[m].tokens += (l.input_tokens || 0) + (l.output_tokens || 0);
  }
  const modelRows = Object.entries(perModel)
    .sort((a, b) => b[1].requests - a[1].requests)
    .slice(0, 8);

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 07 / Analytics</div>
          <h1 className="section-title">Traffic analytics</h1>
        </div>
        <Select
          value={days}
          onChange={setDays}
          options={[
            { value: '1', label: 'Last 24h' },
            { value: '7', label: 'Last 7d' },
            { value: '30', label: 'Last 30d' },
          ]}
        />
      </header>

      <div className="grid-stats">
        <Stat label="Requests" value={(stats?.total_requests ?? 0).toLocaleString()} hint={`${days}d window`} />
        <Stat label="Input tokens" value={(stats?.total_input_tokens ?? 0).toLocaleString()} />
        <Stat label="Output tokens" value={(stats?.total_output_tokens ?? 0).toLocaleString()} />
        <Stat label="Cost" value={`$${(stats?.total_cost_usd ?? 0).toFixed(4)}`} hint="estimated" />
        <Stat label="Avg latency" value={`${Math.round(stats?.avg_latency_ms ?? 0)}ms`} />
        <Stat label="Success" value={`${(stats?.success_rate ?? 100).toFixed(1)}%`} />
        <Stat label="Errors" value={(stats?.error_count ?? 0).toLocaleString()} />
      </div>

      <Card title="Requests per day" eyebrow={`last ${days} days`}>
        <div className="histogram">
          {Object.entries(dayBuckets).map(([day, b]) => {
            const heightPct = (b.count / maxCount) * 100;
            return (
              <div key={day} className="hist-col" title={`${day}: ${b.count} requests, ${b.errors} errors`}>
                <div className="hist-bar-wrap">
                  <div className="hist-bar" style={{ height: `${heightPct}%` }}>
                    {b.errors > 0 && <div className="hist-err" style={{ height: `${(b.errors / Math.max(b.count, 1)) * 100}%` }} />}
                  </div>
                </div>
                <div className="hist-label mono">{day.slice(5)}</div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card title="Top models" eyebrow="by request volume">
        {modelRows.length === 0 ? (
          <div className="empty-box text-sm">No traffic yet.</div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Requests</th>
                  <th>Errors</th>
                  <th>Tokens</th>
                  <th>Error rate</th>
                </tr>
              </thead>
              <tbody>
                {modelRows.map(([m, v]) => {
                  const er = v.requests ? ((v.errors / v.requests) * 100).toFixed(1) : '0.0';
                  return (
                    <tr key={m}>
                      <td className="mono text-sm wrap" style={{ maxWidth: '16rem' }}>
                        {m}
                      </td>
                      <td className="mono text-sm">{v.requests}</td>
                      <td className="mono text-sm">{v.errors}</td>
                      <td className="mono text-sm">{v.tokens.toLocaleString()}</td>
                      <td className="mono text-sm">{er}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
