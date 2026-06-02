'use client';

import { useEffect, useState } from 'react';
import { Card, ErrorState, Loader } from '@/components/UI';
import { api, type RequestLog } from '@/lib/api';

export default function LogsPage() {
  const [logs, setLogs] = useState<RequestLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api.listLogs(50)
      .then(setLogs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <Loader label="Loading request logs" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-[10px] tracking-[0.4em] text-[#6b6358] uppercase mb-2">Section 06 / Telemetry</p>
          <h1 className="font-serif text-5xl italic">Request log</h1>
          <p className="mt-3 text-sm text-[#8a8278] font-mono">{logs.length} requests · last 50 entries</p>
        </div>
        <button onClick={load}
          className="font-mono text-xs uppercase tracking-widest px-6 py-3 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657]">
          Refresh
        </button>
      </header>

      {logs.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="font-serif italic text-2xl text-[#8a8278] mb-2">No requests yet</p>
            <p className="font-mono text-xs text-[#6b6358]">Logs will appear here once you start sending traffic.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-0 border-t border-[#3a342c]">
          <div className="grid grid-cols-12 gap-3 py-2 font-mono text-[10px] uppercase tracking-widest text-[#6b6358] border-b border-[#3a342c]">
            <div className="col-span-3">Time</div>
            <div className="col-span-2">Model</div>
            <div className="col-span-2">Provider</div>
            <div className="col-span-1 text-right">Tokens</div>
            <div className="col-span-1 text-right">Latency</div>
            <div className="col-span-1 text-right">Cost</div>
            <div className="col-span-2 text-right">Status</div>
          </div>
          {logs.map((l) => (
            <div key={l.id} className="grid grid-cols-12 gap-3 py-3 font-mono text-xs text-[#d4cdbf] border-b border-[#2a2520] hover:bg-[#1a1612]">
              <div className="col-span-3 text-[#8a8278]">{new Date(l.created_at).toLocaleString()}</div>
              <div className="col-span-2 text-[#f5f1e8]">{l.model}</div>
              <div className="col-span-2 text-[#8a8278]">{l.provider || '—'}</div>
              <div className="col-span-1 text-right text-[#8a8278]">{(l.input_tokens || 0) + (l.output_tokens || 0)}</div>
              <div className="col-span-1 text-right text-[#8a8278]">{Math.round(l.latency_ms || 0)}ms</div>
              <div className="col-span-1 text-right text-[#d8a657]">${(l.cost_usd || 0).toFixed(4)}</div>
              <div className="col-span-2 text-right">
                <span className={`inline-block px-2 py-0.5 text-[10px] ${
                  l.status_code && l.status_code < 300
                    ? 'bg-[#4a6b3a] text-[#d4e8c4]'
                    : 'bg-[#6b3a3a] text-[#e8c4c4]'
                }`}>
                  {l.status_code || '—'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
