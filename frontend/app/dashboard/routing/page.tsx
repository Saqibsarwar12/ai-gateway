'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import {
  Card,
  Loader,
  ErrorState,
  Button,
  Input,
  Select,
  Modal,
  Badge,
} from '@/components/UI';
import type { Provider, RoutingRule } from '@/lib/api';

const STRATEGIES = [
  { value: 'fallback', label: 'Fallback — try in order' },
  { value: 'round_robin', label: 'Round robin' },
  { value: 'weighted', label: 'Weighted' },
  { value: 'cost', label: 'Cost-optimised' },
  { value: 'latency', label: 'Latency-optimised' },
];

export default function RoutingPage() {
  const { token, apiKey } = useAuth();
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [editing, setEditing] = useState<RoutingRule | null>(null);

  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [r, p] = await Promise.all([
        fetch('https://saki-gateway.indevs.in/admin/routing', { headers }).then((r) => (r.ok ? r.json() : [])),
        fetch('https://saki-gateway.indevs.in/admin/providers', { headers }).then((r) => (r.ok ? r.json() : [])),
      ]);
      setRules(r);
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

  async function toggle(r: RoutingRule) {
    await fetch(`https://saki-gateway.indevs.in/admin/routing/${r.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...headers },
      body: JSON.stringify({ is_active: !r.is_active }),
    });
    load();
  }

  async function remove(r: RoutingRule) {
    if (!confirm(`Delete routing rule "${r.name}"?`)) return;
    await fetch(`https://saki-gateway.indevs.in/admin/routing/${r.id}`, { method: 'DELETE', headers });
    load();
  }

  if (loading) return <Loader label="Loading routing rules" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 03 / Routing</div>
          <h1 className="section-title">Routing rules</h1>
          <p className="section-sub mono">
            {rules.length} rules · {rules.filter((r) => r.is_active).length} active
          </p>
        </div>
        <Button variant="primary" onClick={() => setShowNew(true)} disabled={providers.length === 0}>
          + New rule
        </Button>
      </header>

      {providers.length === 0 && (
        <Card>
          <div className="empty-box">
            <p className="text-sm">No providers yet. Add at least one provider before creating routing rules.</p>
          </div>
        </Card>
      )}

      {rules.length === 0 && providers.length > 0 ? (
        <Card>
          <div className="empty-box">
            <p className="text-sm">No routing rules yet. Rules are how the gateway decides which provider handles which model.</p>
          </div>
        </Card>
      ) : (
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Strategy</th>
                <th>Model pattern</th>
                <th>Providers</th>
                <th>Priority</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>
                    <div style={{ fontWeight: 500 }} className="wrap">
                      {r.name}
                    </div>
                  </td>
                  <td>
                    <Badge variant="default">{r.strategy}</Badge>
                  </td>
                  <td className="mono text-sm">{r.model_pattern || '*'}</td>
                  <td>
                    <div className="row" style={{ flexWrap: 'wrap' }}>
                      {(r.provider_ids || r.provider_order || []).slice(0, 3).map((p) => (
                        <Badge key={p}>{p}</Badge>
                      ))}
                      {(r.provider_ids || r.provider_order || []).length > 3 && (
                        <span className="text-xs dim">+{(r.provider_ids || r.provider_order || []).length - 3}</span>
                      )}
                    </div>
                  </td>
                  <td className="mono text-sm">{r.priority}</td>
                  <td>
                    {r.is_active ? <Badge variant="ok">active</Badge> : <Badge variant="mute">paused</Badge>}
                  </td>
                  <td>
                    <div className="row" style={{ justifyContent: 'flex-end' }}>
                      <Button variant="ghost" size="sm" onClick={() => setEditing(r)}>
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => toggle(r)}>
                        {r.is_active ? 'Pause' : 'Resume'}
                      </Button>
                      <Button variant="danger" size="sm" onClick={() => remove(r)}>
                        Delete
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(showNew || editing) && (
        <RoutingForm
          initial={editing}
          providers={providers}
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

function RoutingForm({
  initial,
  providers,
  headers,
  onClose,
  onSaved,
}: {
  initial: RoutingRule | null;
  providers: Provider[];
  headers: Record<string, string>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(initial?.name || 'default-fallback');
  const [strategy, setStrategy] = useState(initial?.strategy || 'fallback');
  const [modelPattern, setModelPattern] = useState(initial?.model_pattern || '*');
  const [providerIds, setProviderIds] = useState<string[]>(initial?.provider_ids || initial?.provider_order || []);
  const [priority, setPriority] = useState(String(initial?.priority ?? 0));
  const [active, setActive] = useState(initial?.is_active !== false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleProvider(id: string) {
    setProviderIds((curr) => (curr.includes(id) ? curr.filter((x) => x !== id) : [...curr, id]));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = {
        name,
        strategy,
        model_pattern: modelPattern,
        provider_ids: providerIds,
        priority: parseInt(priority),
        is_active: active,
      };
      const url = initial
        ? `https://saki-gateway.indevs.in/admin/routing/${initial.id}`
        : 'https://saki-gateway.indevs.in/admin/routing';
      const method = initial ? 'PUT' : 'POST';
      const r = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        throw new Error(j.detail || `${r.status}`);
      }
      onSaved();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open title={initial ? 'Edit rule' : 'New routing rule'} onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <Input label="Rule name" value={name} onChange={setName} required />
        <Select label="Strategy" value={strategy} onChange={(v) => setStrategy(v as any)} options={STRATEGIES} />
        <Input
          label="Model pattern"
          value={modelPattern}
          onChange={setModelPattern}
          hint="Glob pattern this rule matches, e.g. gpt-4* or *"
        />
        <div>
          <div className="text-xs dim mono" style={{ marginBottom: '0.5rem' }}>
            Providers (in priority order)
          </div>
          <div className="col" style={{ gap: '0.375rem' }}>
            {providers.map((p) => (
              <label key={p.id} className="row" style={{ cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={providerIds.includes(p.id)}
                  onChange={() => toggleProvider(p.id)}
                  style={{ accentColor: 'var(--fg-0)' }}
                />
                <span className="text-sm">{p.name}</span>
                <span className="text-xs dim mono">({p.provider_type})</span>
              </label>
            ))}
          </div>
        </div>
        <div className="grid-2">
          <Input label="Priority" type="number" value={priority} onChange={setPriority} hint="Higher runs first" />
          <Select
            label="Status"
            value={active ? '1' : '0'}
            onChange={(v) => setActive(v === '1')}
            options={[
              { value: '1', label: 'Active' },
              { value: '0', label: 'Paused' },
            ]}
          />
        </div>
        {error && <div className="error-box mono text-sm wrap">{error}</div>}
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" type="submit" disabled={saving}>
            {saving ? 'Saving…' : initial ? 'Save changes' : 'Create rule'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
