'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { apiGetGateway, apiSaveGateway, apiDeleteGateway, apiTestGateway } from '@/lib/api';
import { Button, Card, Input, Loader, Select, Badge } from '@/components/UI';

const providers = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'custom', label: 'Custom OpenAI-compatible' },
];

export default function GatewayPage() {
  const { user } = useAuth();
  const [gateway, setGateway] = useState<any>(null);
  const [provider, setProvider] = useState('openai');
  const [providerType, setProviderType] = useState('openai');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [baseUrl, setBaseUrl] = useState('https://api.openai.com/v1');
  const [enabled, setEnabled] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await apiGetGateway();
      setGateway(data);
      const current = data.configs?.[0];
      if (current) {
        setSelectedId(current.id);
        setProvider(current.provider);
        setProviderType(current.provider_type);
        setModel(current.default_model);
        setBaseUrl(current.base_url);
        setEnabled(current.enabled);
      }
    } catch (err: any) {
      setStatus(err.message || 'Unable to load gateway');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function changeProvider(value: string) {
    setProvider(value);
    setProviderType(value === 'anthropic' ? 'anthropic' : 'openai');
    if (value === 'openai') setBaseUrl('https://api.openai.com/v1');
    if (value === 'anthropic') setBaseUrl('https://api.anthropic.com/v1');
    if (value === 'openrouter') setBaseUrl('https://openrouter.ai/api/v1');
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setStatus(null);
    try {
      const result = await apiSaveGateway({ provider, provider_type: providerType, api_key: apiKey || undefined, default_model: model, base_url: baseUrl, enabled });
      setApiKey('');
      setStatus('Saved securely. Provider key is never displayed again.');
      setGateway((old: any) => ({ ...(old || {}), ...result }));
      await load();
    } catch (err: any) {
      setStatus(err.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }

  async function test() {
    if (!selectedId) return setStatus('Save a provider first.');
    setStatus('Testing provider...');
    try {
      const result = await apiTestGateway(selectedId);
      setStatus(result.ok ? `Provider connected in ${result.latency_ms} ms.` : `Provider test failed${result.error ? `: ${result.error}` : '.'}`);
    } catch (err: any) { setStatus(err.message || 'Provider test failed'); }
  }

  async function remove() {
    if (!selectedId || !confirm('Remove this provider credential?')) return;
    try {
      await apiDeleteGateway(selectedId);
      setSelectedId(null);
      setGateway((old: any) => ({ ...(old || {}), configs: [] }));
      setStatus('Provider credential removed.');
    } catch (err: any) { setStatus(err.message || 'Remove failed'); }
  }

  if (loading) return <Loader label="Loading personal gateway" />;

  return (
    <div className="stack" style={{ maxWidth: '900px' }}>
      <header className="section-head" style={{ marginBottom: '1.5rem' }}>
        <div>
          <div className="section-eyebrow">Section 05 / Personal routing</div>
          <h1 className="section-title" style={{ fontSize: '2.5rem', marginTop: '0.25rem' }}>Your Personal Gateway</h1>
          <p className="text-sm muted">Use your own provider credential through an isolated, authenticated gateway path.</p>
        </div>
      </header>

      <Card title="Personal base URL" eyebrow="Private namespace">
        <code className="code mono text-sm wrap" style={{ display: 'block', padding: '1rem' }}>{gateway?.base_url || 'Configure a provider to generate your URL.'}</code>
        <p className="text-xs muted" style={{ marginTop: '0.75rem' }}>The username in this URL is only a slug. Requests still require your own Saki API key or session token.</p>
      </Card>

      <Card title="Provider configuration" eyebrow="Encrypted at rest">
        <form onSubmit={save} className="stack">
          <Select label="Provider" value={provider} onChange={changeProvider} options={providers} />
          <Input label="Provider API key" type="password" value={apiKey} onChange={setApiKey} placeholder={selectedId ? 'Leave blank to keep the saved key' : 'Paste your provider key'} autoComplete="new-password" required={!selectedId} />
          <Input label="Default model" value={model} onChange={setModel} placeholder="gpt-4o-mini" required />
          <Input label="Base URL" value={baseUrl} onChange={setBaseUrl} placeholder="https://api.openai.com/v1" required />
          <label className="row" style={{ gap: '0.5rem' }}><input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} /> <span className="text-sm">Enable personal gateway</span></label>
          <div className="row" style={{ gap: '0.75rem', flexWrap: 'wrap' }}>
            <Button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save configuration'}</Button>
            {selectedId && <Button type="button" variant="secondary" onClick={test}>Test provider</Button>}
            {selectedId && <Button type="button" variant="danger" onClick={remove}>Remove credential</Button>}
          </div>
          {status && <div className="text-sm muted wrap">{status}</div>}
        </form>
      </Card>

      <Card title="Security" eyebrow="Never exposed">
        <div className="stack" style={{ gap: '0.5rem' }}>
          <div className="row"><Badge variant="ok">Encrypted</Badge><span className="text-sm muted">Provider credentials are encrypted before storage.</span></div>
          <div className="row"><Badge variant="ok">Isolated</Badge><span className="text-sm muted">Only your authenticated identity can use this namespace.</span></div>
          <div className="row"><Badge variant="ok">Hidden</Badge><span className="text-sm muted">API keys are never returned by the dashboard or gateway responses.</span></div>
        </div>
      </Card>
    </div>
  );
}
