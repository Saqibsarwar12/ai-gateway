'use client';

import { useEffect, useState } from 'react';
import { Card, Loader, ErrorState, Stat } from '@/components/UI';
import { useAuth } from '@/lib/auth';

type Analytics = {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
  error_count: number;
};

export default function OverviewPage() {
  const { token, apiKey } = useAuth();
  const [stats, setStats] = useState<Analytics | null>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    else if (apiKey) headers['X-API-Key'] = apiKey;
    Promise.all([
      fetch('https://saki-gateway.indevs.in/admin/analytics?days=7', { headers }).then((r) =>
        r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))
      ),
      fetch('https://saki-gateway.indevs.in/admin/providers', { headers }).then((r) =>
        r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))
      ),
    ])
      .then(([s, p]) => {
        setStats(s);
        setProviders(p);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token, apiKey]);

  if (loading) return <Loader label="Loading overview" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 01 / Overview</div>
          <h1 className="section-title">Operations summary</h1>
          <p className="section-sub mono">Last 7 days · live from the gateway</p>
        </div>
      </header>

      <div className="grid-stats">
        <Stat label="Total requests" value={stats?.total_requests?.toLocaleString() ?? 0} hint="past 7 days" />
        <Stat label="Input tokens" value={stats?.total_input_tokens?.toLocaleString() ?? 0} />
        <Stat label="Output tokens" value={stats?.total_output_tokens?.toLocaleString() ?? 0} />
        <Stat
          label="Cost (USD)"
          value={stats ? `$${stats.total_cost_usd.toFixed(4)}` : '$0.0000'}
          hint={stats?.total_requests ? 'incurred' : 'none yet'}
        />
        <Stat
          label="Avg latency"
          value={stats ? `${stats.avg_latency_ms.toFixed(0)} ms` : '—'}
        />
        <Stat
          label="Success rate"
          value={stats ? `${stats.success_rate.toFixed(1)}%` : '—'}
          hint={stats?.error_count ? `${stats.error_count} errors` : 'no errors'}
        />
        <Stat label="Providers" value={providers.length} hint="configured upstreams" />
        <Stat label="Active" value={providers.filter((p) => p.is_active !== false).length} hint="currently enabled" />
      </div>

      <div className="grid-2" style={{ marginTop: '1rem' }}>
        <Card title="What this is" eyebrow="Section 01">
          <p className="text-sm muted wrap">
            AI Gateway routes OpenAI-compatible chat completions across multiple upstream providers
            (OpenAI, Anthropic, DeepSeek, custom). It exposes a single base URL, an admin console,
            and per-user API keys with credit limits.
          </p>
          <ul className="text-sm muted" style={{ paddingLeft: '1.25rem', lineHeight: 1.8, marginTop: '0.75rem' }}>
            <li>OpenAI-compatible <code className="mono">/v1/chat/completions</code></li>
            <li>Multi-provider fallback routing</li>
            <li>Per-user API keys, credits, role-based access</li>
            <li>Live request logs, analytics, and cost tracking</li>
          </ul>
        </Card>

        <Card title="Base URL" eyebrow="How to call the gateway">
          <pre className="code wrap">https://saki-gateway.indevs.in/v1</pre>
          <p className="text-sm muted" style={{ marginTop: '0.5rem' }}>Use any OpenAI-compatible client:</p>
          <pre className="code wrap">
{`curl https://saki-gateway.indevs.in/v1/chat/completions \\
  -H "Authorization: Bearer $AI_GATEWAY_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"<model>","messages":[{"role":"user","content":"hi"}]}'`}
          </pre>
        </Card>
      </div>
    </div>
  );
}
