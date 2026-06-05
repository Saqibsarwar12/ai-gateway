'use client';

import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/api';
import { Card, Loader, ErrorState, Input, Select, Button, Badge, Modal } from '@/components/UI';
import type { Provider } from '@/lib/api';

type ModelRow = {
  id: string;
  name: string;
  provider_id?: string;
  mode?: string;
};

export default function ModelsPage() {
  const { token, apiKey } = useAuth();
  const [models, setModels] = useState<ModelRow[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [providerFilter, setProviderFilter] = useState('all');
  const [showNew, setShowNew] = useState(false);
  const [syncing, setSyncing] = useState<string | null>(null);

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [m, p] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/models`, { headers }).then((r) => (r.ok ? r.json() : [])),
        fetch(`${API_BASE_URL}/admin/providers`, { headers }).then((r) => (r.ok ? r.json() : [])),
      ]);
      setModels(m);
      setProviders(p);
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

  async function sync(p: Provider) {
    setSyncing(p.id);
    try {
      await fetch(`${API_BASE_URL}/admin/providers/${p.id}/sync-models`, {
        method: 'POST',
        headers,
      });
      await load();
    } finally {
      setSyncing(null);
    }
  }

  const filtered = useMemo(() => {
    return models.filter((m) => {
      if (providerFilter !== 'all' && m.provider_id !== providerFilter) return false;
      if (query && !m.name.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [models, query, providerFilter]);

  if (loading) return <Loader label="Loading models" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 05 / Models</div>
          <h1 className="section-title">Available models</h1>
          <p className="section-sub mono">
            {models.length} models across {providers.length} providers
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowNew(true)} disabled={providers.length === 0}>
          + Add model
        </Button>
      </header>

      <Card>
        <div className="row" style={{ marginBottom: '0.75rem' }}>
          <Input placeholder="Search by name…" value={query} onChange={setQuery} className="flex-1" />
          <Select
            value={providerFilter}
            onChange={setProviderFilter}
            options={[
              { value: 'all', label: 'All providers' },
              ...providers.map((p) => ({ value: p.id, label: p.name })),
            ]}
          />
        </div>

        {providers.length > 0 && (
          <div className="stack" style={{ marginBottom: '1rem' }}>
            <div className="section-eyebrow">Sync from provider</div>
            <div className="row" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
              {providers.map((p) => (
                <Button
                  key={p.id}
                  variant="secondary"
                  size="sm"
                  onClick={() => sync(p)}
                  disabled={syncing === p.id || !p.api_key}
                  title={!p.api_key ? 'Provider has no API key configured' : ''}
                >
                  {syncing === p.id ? 'Syncing…' : `↻ ${p.name}`}
                </Button>
              ))}
            </div>
          </div>
        )}

        {filtered.length === 0 ? (
          <div className="empty-box">
            <p className="text-sm">No models found. Sync from a provider or add one manually.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Provider</th>
                  <th>Mode</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((m) => {
                  const prov = providers.find((p) => p.id === m.provider_id);
                  return (
                    <tr key={m.id}>
                      <td className="mono text-sm wrap">{m.name}</td>
                      <td>
                        {prov ? <Badge>{prov.name}</Badge> : <span className="dim text-xs">unassigned</span>}
                      </td>
                      <td>
                        <Badge variant="mute">{m.mode || 'chat'}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {showNew && (
        <NewModelForm
          providers={providers}
          headers={headers}
          onClose={() => setShowNew(false)}
          onCreated={() => {
            setShowNew(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function NewModelForm({
  providers,
  headers,
  onClose,
  onCreated,
}: {
  providers: Provider[];
  headers: Record<string, string>;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState('');
  const [modelId, setModelId] = useState('');
  const [providerId, setProviderId] = useState(providers[0]?.id || '');
  const [mode, setMode] = useState('chat');
  const [contextWindow, setContextWindow] = useState('8192');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE_URL}/admin/models`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify({
          name,
          model_id: modelId,
          provider_id: providerId,
          mode,
          context_window: parseInt(contextWindow),
        }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `${r.status}`);
      }
      onCreated();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title="Add model" onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <Input label="Display name" value={name} onChange={setName} required placeholder="e.g. GPT-4o mini" />
        <Input label="Model ID" value={modelId} onChange={setModelId} required placeholder="e.g. gpt-4o-mini" />
        <Select
          label="Provider"
          value={providerId}
          onChange={setProviderId}
          options={providers.map((p) => ({ value: p.id, label: p.name }))}
        />
        <div className="grid-2">
          <Select
            label="Mode"
            value={mode}
            onChange={setMode}
            options={[
              { value: 'chat', label: 'Chat' },
              { value: 'completion', label: 'Completion' },
              { value: 'embedding', label: 'Embedding' },
            ]}
          />
          <Input label="Context window" type="number" value={contextWindow} onChange={setContextWindow} />
        </div>
        {error && <div className="error-box mono text-sm wrap">{error}</div>}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Add model'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
