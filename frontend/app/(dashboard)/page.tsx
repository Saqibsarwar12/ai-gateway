'use client';

import { useEffect, useState } from 'react';
import { Card, StatCard as Stat, ErrorState, Loader } from '@/components/UI';
import { api, type Provider, type AIModel as Model, type User } from '@/lib/api';

export default function OverviewPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.listProviders(), api.listUsers()])
      .then(([p, u]) => {
        setProviders(p);
        setUsers(u);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader label="Loading overview" />;
  if (error) return <ErrorState error={error} />;

  const enabled = providers.filter((p) => p.is_active !== false && p.enabled !== false).length;
  const total = providers.length;

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-[10px] tracking-[0.4em] text-[#6b6358] uppercase mb-2">Section 01 / Overview</p>
          <h1 className="font-serif text-5xl italic">Gateway status</h1>
        </div>
        <div className="text-right">
          <p className="font-mono text-[10px] text-[#6b6358] uppercase tracking-widest">Last sync</p>
          <p className="font-mono text-sm text-[#f5f1e8]">{new Date().toLocaleTimeString()}</p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border-t border-b border-[#3a342c]">
        <Stat label="Providers" value={`${enabled}/${total}`} accent="cyan" />
        <Stat label="Users" value={String(users.length)} />
        <Stat label="Status" value="Online" accent="acid" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Active providers" subtitle="Upstreams reachable from the gateway">
          {providers.length === 0 ? (
            <p className="font-mono text-xs text-[#6b6358]">No providers configured yet.</p>
          ) : (
            <ul className="divide-y divide-[#2a2520]">
              {providers.slice(0, 6).map((p) => (
                <li key={p.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="font-serif text-lg text-[#f5f1e8]">{p.name}</p>
                    <p className="font-mono text-[10px] text-[#6b6358] uppercase tracking-wider">{p.provider_type}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-xs text-[#f5f1e8]">{(p.models || []).length} models</p>
                    <p className="font-mono text-[10px] text-[#6b6358]">{p.base_url}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Quick start" subtitle="Get to a working provider in 60 seconds">
          <ol className="space-y-3 font-serif text-base text-[#d4cdbf]">
            <li><span className="font-mono text-xs text-[#d8a657] mr-3">01</span>Add your first upstream provider</li>
            <li><span className="font-mono text-xs text-[#d8a657] mr-3">02</span>Run a health check</li>
            <li><span className="font-mono text-xs text-[#d8a657] mr-3">03</span>Send a chat completion via the OpenAI-compatible API</li>
          </ol>
          <pre className="mt-6 p-4 bg-[#0a0908] border border-[#2a2520] text-[10px] font-mono text-[#8a8278] overflow-x-auto">
{`curl -X POST https://ai-gateway-7dkh.onrender.com/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'`}
          </pre>
        </Card>
      </div>
    </div>
  );
}
