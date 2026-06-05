'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/api';
import { Card, Loader, ErrorState, Button, Input, Select, Modal, Badge } from '@/components/UI';
import type { Provider } from '@/lib/api';

const PROVIDER_TYPES = [
  { v: 'openai', l: 'OpenAI / compatible' },
  { v: 'anthropic', l: 'Anthropic' },
  { v: 'gemini', l: 'Google Gemini' },
  { v: 'deepseek', l: 'DeepSeek' },
  { v: 'groq', l: 'Groq' },
  { v: 'ollama', l: 'Ollama (local)' },
  { v: 'openrouter', l: 'OpenRouter' },
  { v: 'custom', l: 'Custom (OpenAI-compatible)' },
];

const PRESETS: Record<string, string> = {
  openai: 'https://api.openai.com/v1',
  anthropic: 'https://api.anthropic.com/v1',
  gemini: 'https://generativelanguage.googleapis.com/v1beta/openai',
  deepseek: 'https://api.deepseek.com/v1',
  groq: 'https://api.groq.com/openai/v1',
  ollama: 'http://localhost:11434/v1',
  openrouter: 'https://openrouter.ai/api/v1',
  custom: '',
};

export default function ProvidersPage() {
  const { token, apiKey } = useAuth();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Provider | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; latency_ms: number; error?: string }>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE_URL}/admin/providers`, { headers });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      setProviders(await r.json());
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

  async function deleteProvider(id: string) {
    if (!confirm('Delete this provider? Models routed to it will be unavailable.')) return;
    await fetch(`${API_BASE_URL}/admin/providers/${id}`, { method: 'DELETE', headers });
    load();
  }
  async function testProvider(id: string) {
    setTestingId(id);
    try {
      const r = await fetch(`${API_BASE_URL}/admin/providers/${id}/test`, { method: 'POST', headers });
      const data = await r.json();
      setTestResults((m) => ({ ...m, [id]: data }));
    } catch (e: any) {
      setTestResults((m) => ({ ...m, [id]: { ok: false, latency_ms: 0, error: e.message } }));
    }
    setTestingId(null);
  }
  async function syncModels(id: string) {
    setSyncingId(id);
    try {
      const r = await fetch(`${API_BASE_URL}/admin/providers/${id}/sync-models`, { method: 'POST', headers });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      alert(`Synced ${data.total} models (${data.created} new, ${data.updated} updated).`);
    } catch (e: any) {
      alert(`Sync failed: ${e.message}`);
    }
    setSyncingId(null);
  }

  if (loading) return <Loader label="Loading providers" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 02 / Providers</div>
          <h1 className="section-title">Upstream gateways</h1>
          <p className="section-sub mono">
            {providers.length} configured · {providers.filter((p) => p.is_active !== false).length} active
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowNew(true)}>
          + Add provider
        </Button>
      </header>

      {providers.length === 0 ? (
        <Card>
          <div className="empty-box">
            <div style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>No providers configured</div>
            <p className="text-sm muted" style={{ marginBottom: '1rem' }}>
              Add an upstream to start routing requests through the gateway.
            </p>
            <Button variant="primary" onClick={() => setShowNew(true)}>
              + Add your first provider
            </Button>
          </div>
        </Card>
      ) : (
        <Card>
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Base URL</th>
                  <th>Models</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((p) => {
                  const t = testResults[p.id];
                  return (
                    <tr key={p.id}>
                      <td>
                        <div style={{ fontWeight: 500, color: 'var(--fg-0)' }}>{p.name}</div>
                        <div className="mono text-xs dim">{p.id}</div>
                      </td>
                      <td>
                        <Badge>{p.provider_type}</Badge>
                      </td>
                      <td className="mono text-xs wrap" style={{ maxWidth: '14rem', color: 'var(--fg-2)' }}>
                        {p.base_url}
                      </td>
                      <td className="mono text-xs">{(p.models || []).length}</td>
                      <td>
                        {t ? (
                          t.ok ? (
                            <Badge variant="ok">● {t.latency_ms}ms</Badge>
                          ) : (
                            <Badge variant="err">✕ {t.error?.slice(0, 24) || 'fail'}</Badge>
                          )
                        ) : (
                          <span className="dim text-xs">—</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="row" style={{ justifyContent: 'flex-end' }}>
                          <Button size="sm" variant="ghost" onClick={() => testProvider(p.id)} disabled={testingId === p.id}>
                            {testingId === p.id ? '…' : 'Test'}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => syncModels(p.id)} disabled={syncingId === p.id}>
                            {syncingId === p.id ? '…' : 'Sync'}
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setEditing(p)}>
                            Edit
                          </Button>
                          <Button size="sm" variant="danger" onClick={() => deleteProvider(p.id)}>
                            ×
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {(showNew || editing) && (
        <ProviderForm
          initial={editing}
          headers={headers}
          onClose={() => {
            setShowNew(false);
            setEditing(null);
          }}
          onSaved={() => {
            setShowNew(false);
            setEditing(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function ProviderForm({
  initial,
  headers,
  onClose,
  onSaved,
}: {
  initial: Provider | null;
  headers: Record<string, string>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(initial?.name || '');
  const [providerType, setProviderType] = useState(initial?.provider_type || 'openai');
  const [baseUrl, setBaseUrl] = useState(initial?.base_url || PRESETS.openai);
  const [apiKey, setApiKey] = useState('');
  const [models, setModels] = useState((initial?.models || []).join(', '));
  const [priority, setPriority] = useState(initial?.priority ?? 100);
  const [enabled, setEnabled] = useState(initial?.is_active !== false && initial?.enabled !== false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onTypeChange(t: string) {
    setProviderType(t);
    if (PRESETS[t] && !baseUrl) setBaseUrl(PRESETS[t]);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const data = {
        name,
        provider_type: providerType,
        base_url: baseUrl,
        ...(apiKey ? { api_key: apiKey } : {}),
        models: models.split(',').map((m) => m.trim()).filter(Boolean),
        priority,
        enabled,
        is_active: enabled,
      };
      const url = initial
        ? `${API_BASE_URL}/admin/providers/${initial.id}`
        : `${API_BASE_URL}/admin/providers`;
      const method = initial ? 'PUT' : 'POST';
      const r = await fetch(url, {
        method,
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `${r.status} ${r.statusText}`);
      }
      onSaved();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={initial ? `Edit provider · ${initial.name}` : 'Add provider'} onClose={onClose} width="lg">
      <form onSubmit={submit} className="stack">
        <div className="grid-2">
          <Input label="Name" value={name} onChange={setName} placeholder="OpenAI main" required />
          <Select
            label="Provider type"
            value={providerType}
            onChange={onTypeChange}
            options={PROVIDER_TYPES.map((t) => ({ value: t.v, label: t.l }))}
          />
        </div>
        <Input
          label="Base URL"
          value={baseUrl}
          onChange={setBaseUrl}
          placeholder="https://api.openai.com/v1"
          required
          hint="OpenAI-compatible endpoint."
        />
        <Input
          label="API key"
          value={apiKey}
          onChange={setApiKey}
          type="password"
          placeholder={initial?.api_key || 'leave blank to keep existing key'}
          hint={initial?.api_key ? `Current: ${initial.api_key}` : 'Stored encrypted at rest.'}
        />
        <Input
          label="Models (comma-separated, optional)"
          value={models}
          onChange={setModels}
          placeholder="gpt-4o, gpt-4o-mini"
          hint="Use Sync Models to auto-populate after saving."
        />
        <div className="grid-2">
          <Input label="Priority" value={String(priority)} onChange={(v) => setPriority(parseInt(v || '100'))} type="number" />
          <div>
            <label className="lbl">Enabled</label>
            <label className="row" style={{ padding: '0.5rem 0', cursor: 'pointer' }}>
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              <span className="text-sm">Active — receive traffic</span>
            </label>
          </div>
        </div>
        {error && <div className="error-box text-sm wrap mono">{error}</div>}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={saving}>
            {saving ? 'Saving…' : initial ? 'Save changes' : 'Create provider'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
