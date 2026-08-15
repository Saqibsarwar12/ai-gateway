'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { API_BASE_URL } from '@/lib/api';
import { Badge, Button, Card, ErrorState, Input, Loader } from '@/components/UI';

type Config = {
  configured: boolean;
  id?: string;
  display_name: string;
  public_model_id: string;
  base_url: string;
  enabled: boolean;
  account_count?: number;
};

type Account = {
  id: string;
  label: string;
  model_id: string;
  enabled: boolean;
  status: string;
  cooldown_until?: string | null;
  success_count: number;
  failure_count: number;
  avg_latency_ms: number;
  last_status_code?: number | null;
  has_api_key: boolean;
};

export default function NvidiaSmartPage() {
  const { token, user } = useAuth();
  const headers = { Authorization: `Bearer ${token}` };
  const [config, setConfig] = useState<Config | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('NVIDIA Smart');
  const [publicModelId, setPublicModelId] = useState('nvidia-smart');
  const [enabled, setEnabled] = useState(true);
  const [label, setLabel] = useState('');
  const [modelId, setModelId] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/nvidia-smart/configuration`, { headers });
      if (!res.ok) throw new Error(`Failed to load NVIDIA Smart (${res.status})`);
      const data = await res.json();
      setConfig(data.config);
      setAccounts(data.accounts || []);
      setDisplayName(data.config.display_name);
      setPublicModelId(data.config.public_model_id);
      setEnabled(data.config.enabled);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (user?.role === 'admin') load();
    else setLoading(false);
  }, [user?.role]);

  async function saveConfig(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/nvidia-smart/config`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ display_name: displayName, public_model_id: publicModelId, enabled }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Could not save configuration');
      setMessage('Configuration saved.');
      await load();
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function addAccount(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/nvidia-smart/accounts`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ label, model_id: modelId, api_key: apiKey, enabled: true }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Could not add account');
      setLabel('');
      setModelId('');
      setApiKey('');
      setMessage('NVIDIA account added. The key is never shown again.');
      await load();
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleAccount(account: Account) {
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/nvidia-smart/accounts/${account.id}`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: account.label, model_id: account.model_id, enabled: !account.enabled }),
      });
      if (!res.ok) throw new Error('Could not update account');
      await load();
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteAccount(account: Account) {
    if (!window.confirm(`Delete ${account.label}?`)) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/nvidia-smart/accounts/${account.id}`, { method: 'DELETE', headers });
      if (!res.ok) throw new Error('Could not delete account');
      await load();
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function testAll() {
    setTesting(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_BASE_URL}/admin/nvidia-smart/test`, { method: 'POST', headers });
      const data = await res.json();
      setMessage(data.ok ? `All ${data.tested} enabled accounts responded.` : `NVIDIA test completed: ${data.tested || 0} tested. Check each account status for a sanitized upstream result.`);
      await load();
    } catch (e: any) {
      setMessage(e.message);
    } finally {
      setTesting(false);
    }
  }

  if (user && user.role !== 'admin') return <ErrorState error="Admin role required" />;
  if (loading) return <Loader label="Loading NVIDIA Smart" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Admin-only routing</div>
          <h1 className="section-title">NVIDIA Smart</h1>
          <p className="section-sub mono">One public model · up to 50 NVIDIA API accounts</p>
        </div>
        <Button variant="secondary" onClick={testAll} disabled={testing || accounts.length === 0}>{testing ? 'Testing…' : 'Test all accounts'}</Button>
      </header>

      <Card title="Public model" eyebrow="single gateway identity">
        <form onSubmit={saveConfig} className="stack">
          <div className="grid-2">
            <Input label="Display name" value={displayName} onChange={setDisplayName} required />
            <Input label="Public model ID" value={publicModelId} onChange={setPublicModelId} required hint="Clients send this model ID to /v1." />
          </div>
          <div className="row">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
            <span className="text-sm">Enabled for gateway traffic</span>
          </div>
          <div className="text-sm muted">Upstream base URL is fixed to <span className="mono">{config?.base_url || 'https://integrate.api.nvidia.com/v1'}</span>.</div>
          {message && <div className="text-sm muted wrap">{message}</div>}
          <Button type="submit" variant="primary" disabled={saving}>{saving ? 'Saving…' : 'Save NVIDIA Smart'}</Button>
        </form>
      </Card>

      <Card title={`NVIDIA accounts (${accounts.length}/50)`} eyebrow="encrypted credentials">
        <form onSubmit={addAccount} className="stack" style={{ marginBottom: '1.25rem' }}>
          <div className="grid-2">
            <Input label="Internal label" value={label} onChange={setLabel} placeholder="Account 1" required />
            <Input label="NVIDIA model ID" value={modelId} onChange={setModelId} placeholder="nvidia/llama-3.3-nemotron-super-49b-v1" required />
          </div>
          <Input label="NVIDIA API key" value={apiKey} onChange={setApiKey} type="password" required autoComplete="off" />
          <div className="text-xs muted">Keys are encrypted before storage and are never returned by the API or shown in logs.</div>
          <Button type="submit" variant="secondary" disabled={saving || accounts.length >= 50}>{saving ? 'Adding…' : 'Add NVIDIA account'}</Button>
        </form>
        {accounts.length === 0 ? <div className="empty-box text-sm muted">No NVIDIA accounts configured.</div> : (
          <div className="table-wrap">
            <table className="tbl"><thead><tr><th>Account</th><th>Model</th><th>Status</th><th>Success / failures</th><th>Actions</th></tr></thead>
              <tbody>{accounts.map((account) => <tr key={account.id}>
                <td><div>{account.label}</div><div className="text-xs dim mono">{account.has_api_key ? 'credential stored' : 'missing credential'}</div></td>
                <td className="mono text-xs wrap">{account.model_id}</td>
                <td><Badge variant={account.status === 'healthy' ? 'ok' : account.status === 'cooling_down' ? 'warn' : 'err'}>{account.status}</Badge></td>
                <td className="mono text-xs">{account.success_count} / {account.failure_count}</td>
                <td><div className="row"><Button size="sm" variant="ghost" onClick={() => toggleAccount(account)} disabled={saving}>{account.enabled ? 'Disable' : 'Enable'}</Button><Button size="sm" variant="danger" onClick={() => deleteAccount(account)} disabled={saving}>Delete</Button></div></td>
              </tr>)}</tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
