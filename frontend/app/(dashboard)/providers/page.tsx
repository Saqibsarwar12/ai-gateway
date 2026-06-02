'use client';

import { useEffect, useState, useRef } from 'react';
import { Card, ErrorState, Loader, Modal } from '@/components/UI';
import { api, type Provider } from '@/lib/api';

const PROVIDER_TYPES = ['openai', 'anthropic', 'gemini', 'deepseek', 'groq', 'ollama', 'openrouter', 'custom'];

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Provider | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, { ok: boolean; latency_ms: number; detail?: string }>>({});

  const load = () => {
    setLoading(true);
    api.listProviders()
      .then(setProviders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this provider?')) return;
    await api.deleteProvider(id);
    load();
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const result = await api.testProvider(id);
      setTestResult((r) => ({ ...r, [id]: result }));
    } catch (e: any) {
      setTestResult((r) => ({ ...r, [id]: { ok: false, latency_ms: 0, detail: e.message } }));
    }
    setTesting(null);
  };

  if (loading) return <Loader label="Loading providers" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-[10px] tracking-[0.4em] text-[#6b6358] uppercase mb-2">Section 02 / Providers</p>
          <h1 className="font-serif text-5xl italic">Upstream gateways</h1>
          <p className="mt-3 text-sm text-[#8a8278] font-mono">{providers.length} configured · {providers.filter(p => p.is_active !== false).length} active</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="font-mono text-xs uppercase tracking-widest px-6 py-3 bg-[#d8a657] text-[#0a0908] hover:bg-[#e8b867] transition"
        >
          + Add provider
        </button>
      </header>

      {providers.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="font-serif italic text-2xl text-[#8a8278] mb-2">No providers yet</p>
            <p className="font-mono text-xs text-[#6b6358]">Add your first upstream to start routing requests.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-0 border-t border-[#3a342c]">
          {providers.map((p) => {
            const test = testResult[p.id];
            return (
              <div key={p.id} className="border-b border-[#2a2520] py-6 grid grid-cols-12 gap-4 items-center">
                <div className="col-span-12 md:col-span-4">
                  <p className="font-serif text-2xl text-[#f5f1e8]">{p.name}</p>
                  <p className="font-mono text-[10px] text-[#6b6358] uppercase tracking-widest mt-1">{p.provider_type}</p>
                </div>
                <div className="col-span-12 md:col-span-3 font-mono text-[11px] text-[#8a8278] truncate">
                  {p.base_url}
                </div>
                <div className="col-span-6 md:col-span-2 font-mono text-xs text-[#f5f1e8]">
                  {(p.models || []).length} models
                </div>
                <div className="col-span-6 md:col-span-3 flex items-center justify-end gap-2">
                  {test && (
                    <span className={`font-mono text-[10px] px-2 py-1 ${test.ok ? 'bg-[#4a6b3a] text-[#d4e8c4]' : 'bg-[#6b3a3a] text-[#e8c4c4]'}`}>
                      {test.ok ? `${test.latency_ms}ms` : 'fail'}
                    </span>
                  )}
                  <button
                    onClick={() => handleTest(p.id)}
                    disabled={testing === p.id}
                    className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657] disabled:opacity-50"
                  >
                    {testing === p.id ? '...' : 'Test'}
                  </button>
                  <button
                    onClick={() => setEditing(p)}
                    className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657]"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border border-[#6b3a3a] text-[#e8c4c4] hover:bg-[#6b3a3a] hover:text-[#0a0908]"
                  >
                    ×
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {(showNew || editing) && (
        <ProviderForm
          initial={editing}
          onClose={() => { setShowNew(false); setEditing(null); }}
          onSaved={() => { setShowNew(false); setEditing(null); load(); }}
        />
      )}
    </div>
  );
}

function ProviderForm({ initial, onClose, onSaved }: { initial: Provider | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(initial?.name || '');
  const [providerType, setProviderType] = useState(initial?.provider_type || 'openai');
  const [baseUrl, setBaseUrl] = useState(initial?.base_url || 'https://api.openai.com/v1');
  const [apiKey, setApiKey] = useState(initial?.api_key || '');
  const [models, setModels] = useState((initial?.models || []).join(', '));
  const [priority, setPriority] = useState(initial?.priority ?? 100);
  const [enabled, setEnabled] = useState(initial?.is_active !== false && initial?.enabled !== false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const data = {
        name,
        provider_type: providerType,
        base_url: baseUrl,
        api_key: apiKey,
        models: models.split(',').map((m) => m.trim()).filter(Boolean),
        priority,
        enabled,
        is_active: enabled,
      };
      if (initial) {
        await api.updateProvider(initial.id, data);
      } else {
        await api.createProvider(data);
      }
      onSaved();
    } catch (e: any) {
      setError(e.message);
    }
    setSaving(false);
  };

  return (
    <Modal open title={initial ? 'Edit provider' : 'New provider'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <Field label="Name">
          <input value={name} onChange={(e: any) => setName(e.target.value)} required
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
        </Field>
        <Field label="Type">
          <select value={providerType} onChange={(e: any) => setProviderType(e.target.value)}
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none">
            {PROVIDER_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="Base URL">
          <input value={baseUrl} onChange={(e: any) => setBaseUrl(e.target.value)} required
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
        </Field>
        <Field label="API key">
          <input type="password" value={apiKey} onChange={(e: any) => setApiKey(e.target.value)}
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
        </Field>
        <Field label="Models (comma-separated)">
          <input value={models} onChange={(e) => setModels(e.target.value)} placeholder="gpt-4o-mini, gpt-4o"
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Priority">
            <input type="number" value={priority} onChange={(e) => setPriority(Number(e.target.value))}
              className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
          </Field>
          <Field label="Enabled">
            <label className="flex items-center gap-2 mt-2 cursor-pointer">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="accent-[#d8a657]" />
              <span className="font-mono text-xs text-[#f5f1e8]">Active</span>
            </label>
          </Field>
        </div>
        {error && <p className="text-xs font-mono text-[#e8c4c4] bg-[#3a1a1a] p-3 border border-[#6b3a3a]">{error}</p>}
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving}
            className="flex-1 font-mono text-xs uppercase tracking-widest py-3 bg-[#d8a657] text-[#0a0908] hover:bg-[#e8b867] disabled:opacity-50">
            {saving ? 'Saving…' : initial ? 'Save changes' : 'Create provider'}
          </button>
          <button type="button" onClick={onClose}
            className="font-mono text-xs uppercase tracking-widest py-3 px-6 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657]">
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="block font-mono text-[10px] uppercase tracking-widest text-[#6b6358] mb-1.5">{label}</span>
      {children}
    </label>
  );
}
