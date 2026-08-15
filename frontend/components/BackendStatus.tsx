'use client';

import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from '@/lib/api';
import { Badge, Button, Card, Spinner } from '@/components/UI';

const UPTIME_URL = 'https://uptimesignal.io/status/saki-gateway';

type HealthState = 'checking' | 'up' | 'down';

type HealthResponse = {
  status?: string;
  version?: string;
};

export default function BackendStatus() {
  const [state, setState] = useState<HealthState>('checking');
  const [latency, setLatency] = useState<number | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);

  const checkHealth = useCallback(async () => {
    setState('checking');
    const started = performance.now();
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      });
      const body = (await response.json().catch(() => ({}))) as HealthResponse;
      if (!response.ok || body.status !== 'ok') throw new Error('Backend health check failed');
      setLatency(Math.round(performance.now() - started));
      setVersion(body.version || null);
      setState('up');
    } catch {
      setLatency(null);
      setVersion(null);
      setState('down');
    } finally {
      setCheckedAt(new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }
  }, []);

  useEffect(() => {
    void checkHealth();
    const timer = window.setInterval(() => void checkHealth(), 60_000);
    return () => window.clearInterval(timer);
  }, [checkHealth]);

  const label = state === 'checking' ? 'Checking' : state === 'up' ? 'Operational' : 'Unavailable';
  const variant = state === 'up' ? 'ok' : state === 'down' ? 'err' : 'mute';

  return (
    <Card
      eyebrow="Runtime health"
      title="Backend and API status"
      action={
        <a href={UPTIME_URL} target="_blank" rel="noreferrer" className="btn btn-secondary" style={{ padding: '0.4375rem 0.6875rem', fontSize: '0.75rem' }}>
          UptimeSignal ↗
        </a>
      }
    >
      <div className="between">
        <div className="row" style={{ gap: '0.625rem' }}>
          {state === 'checking' ? <Spinner size={10} /> : <span className={`dot ${state === 'up' ? 'dot-ok' : 'dot-err'}`} />}
          <Badge variant={variant}>{label}</Badge>
          <span className="text-sm muted mono">{API_BASE_URL || 'same-origin'} /health</span>
        </div>
        <Button variant="ghost" size="sm" onClick={() => void checkHealth} disabled={state === 'checking'}>Check now</Button>
      </div>
      <div className="row" style={{ marginTop: '0.75rem', gap: '1rem', flexWrap: 'wrap' }}>
        <span className="text-xs muted mono">{latency === null ? '—' : `${latency} ms response`}</span>
        {version && <span className="text-xs muted mono">v{version}</span>}
        {checkedAt && <span className="text-xs dim mono">checked {checkedAt}</span>}
      </div>
      {state === 'down' && <div className="text-xs muted wrap" style={{ marginTop: '0.75rem' }}>The dashboard could not get a healthy JSON response from the gateway. Open UptimeSignal for incident history.</div>}
    </Card>
  );
}
