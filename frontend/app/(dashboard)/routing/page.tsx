'use client';

import { useEffect, useState } from 'react';
import { Card, ErrorState, Loader, Modal } from '@/components/UI';
import { api, type RoutingRule, type Provider } from '@/lib/api';

const STRATEGIES = [
  { value: 'fallback', label: 'Fallback (try in order)' },
  { value: 'priority', label: 'Priority (lowest number first)' },
  { value: 'cost', label: 'Cheapest first' },
  { value: 'latency', label: 'Lowest latency first' },
  { value: 'round_robin', label: 'Round robin' },
  { value: 'weighted', label: 'Weighted' },
];

export default function RoutingPage() {
  const [rules, setRules] = useState<RoutingRule[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<RoutingRule | null>(null);
  const [showNew, setShowNew] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([api.listRules(), api.listProviders()])
      .then(([r, p]) => { setRules(r); setProviders(p); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this routing rule?')) return;
    await api.deleteRule(id);
    load();
  };

  if (loading) return <Loader label="Loading routing rules" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-[10px] tracking-[0.4em] text-[#6b6358] uppercase mb-2">Section 05 / Routing</p>
          <h1 className="font-serif text-5xl italic">Rules of dispatch</h1>
          <p className="mt-3 text-sm text-[#8a8278] font-mono">{rules.length} active · {providers.length} providers available</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="font-mono text-xs uppercase tracking-widest px-6 py-3 bg-[#d8a657] text-[#0a0908] hover:bg-[#e8b867] transition"
        >
          + New rule
        </button>
      </header>

      {rules.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="font-serif italic text-2xl text-[#8a8278] mb-2">No routing rules yet</p>
            <p className="font-mono text-xs text-[#6b6358]">Rules determine how requests are dispatched across providers.</p>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {rules.map((r) => (
            <Card key={r.id}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-[#6b6358] mb-1">Strategy · {r.strategy}</p>
                  <h3 className="font-serif text-2xl text-[#f5f1e8]">{r.name}</h3>
                  <p className="font-mono text-xs text-[#8a8278] mt-2">Pattern: <span className="text-[#d8a657]">{r.model_pattern || '*'}</span></p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {(r.provider_ids || []).map((pid, i) => {
                      const p = providers.find((x) => x.id === pid);
                      return (
                        <span key={i} className="font-mono text-[10px] px-2 py-1 bg-[#1a1612] border border-[#3a342c] text-[#d4cdbf]">
                          {i + 1}. {p?.name || pid.slice(0, 8)}
                        </span>
                      );
                    })}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`font-mono text-[10px] px-2 py-1 ${r.is_active !== false ? 'bg-[#4a6b3a] text-[#d4e8c4]' : 'bg-[#3a342c] text-[#8a8278]'}`}>
                    {r.is_active !== false ? 'ACTIVE' : 'PAUSED'}
                  </span>
                  <button onClick={() => setEditing(r)}
                    className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657]">
                    Edit
                  </button>
                  <button onClick={() => handleDelete(r.id)}
                    className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border border-[#6b3a3a] text-[#e8c4c4] hover:bg-[#6b3a3a] hover:text-[#0a0908]">
                    ×
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {(showNew || editing) && (
        <RuleForm initial={editing} providers={providers}
          onClose={() => { setShowNew(false); setEditing(null); }}
          onSaved={() => { setShowNew(false); setEditing(null); load(); }} />
      )}
    </div>
  );
}

function RuleForm({ initial, providers, onClose, onSaved }: { initial: RoutingRule | null; providers: Provider[]; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(initial?.name || '');
  const [strategy, setStrategy] = useState<any>(initial?.strategy || 'fallback');
  const [modelPattern, setModelPattern] = useState(initial?.model_pattern || '*');
  const [providerOrder, setProviderOrder] = useState<string[]>(initial?.provider_ids || []);
  const [fallback, setFallback] = useState(initial?.fallback_enabled !== false);
  const [maxRetries, setMaxRetries] = useState(initial?.max_retries ?? 2);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleProvider = (id: string) => {
    setProviderOrder((p) => p.includes(id) ? p.filter((x) => x !== id) : [...p, id]);
  };

  const moveProvider = (id: string, dir: -1 | 1) => {
    setProviderOrder((p) => {
      const idx = p.indexOf(id);
      if (idx < 0) return p;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= p.length) return p;
      const next = [...p];
      [next[idx], next[newIdx]] = [next[newIdx], next[idx]];
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const data = {
        name,
        strategy,
        model_pattern: modelPattern,
        provider_order: providerOrder,
        provider_ids: providerOrder,
        fallback_enabled: fallback,
        max_retries: maxRetries,
        is_active: true,
      };
      if (initial) {
        await api.updateRule(initial.id, data);
      } else {
        await api.createRule(data);
      }
      onSaved();
    } catch (e: any) {
      setError(e.message);
    }
    setSaving(false);
  };

  return (
    <Modal open title={initial ? 'Edit rule' : 'New rule'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <Field label="Name">
          <input value={name} onChange={(e: any) => setName(e.target.value)} required
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
        </Field>
        <Field label="Strategy">
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none">
            {STRATEGIES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </Field>
        <Field label="Model pattern (e.g. gpt-4*, * for all)">
          <input value={modelPattern} onChange={(e: any) => setModelPattern(e.target.value)} placeholder="*"
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
        </Field>
        <Field label="Provider order (click to add, drag arrows to reorder)">
          <div className="space-y-1.5 max-h-64 overflow-y-auto">
            {providers.length === 0 && (
              <p className="font-mono text-xs text-[#6b6358] py-3">No providers configured — add some first.</p>
            )}
            {providers.map((p) => {
              const order = providerOrder.indexOf(p.id);
              const selected = order >= 0;
              return (
                <div key={p.id}
                  className={`flex items-center gap-2 px-3 py-2 border cursor-pointer ${
                    selected ? 'border-[#d8a657] bg-[#1a1612]' : 'border-[#3a342c] hover:border-[#6b6358]'
                  }`}
                  onClick={() => toggleProvider(p.id)}>
                  {selected && <span className="font-mono text-[10px] text-[#d8a657] w-5">{order + 1}.</span>}
                  <span className="font-serif text-sm text-[#f5f1e8] flex-1">{p.name}</span>
                  <span className="font-mono text-[10px] text-[#6b6358]">{p.provider_type}</span>
                  {selected && (
                    <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                      <button type="button" onClick={() => moveProvider(p.id, -1)} className="text-[#6b6358] hover:text-[#d8a657] px-1">↑</button>
                      <button type="button" onClick={() => moveProvider(p.id, 1)} className="text-[#6b6358] hover:text-[#d8a657] px-1">↓</button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Max retries">
            <input type="number" value={maxRetries} onChange={(e) => setMaxRetries(Number(e.target.value))}
              className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
          </Field>
          <Field label="Fallback enabled">
            <label className="flex items-center gap-2 mt-2 cursor-pointer">
              <input type="checkbox" checked={fallback} onChange={(e) => setFallback(e.target.checked)} className="accent-[#d8a657]" />
              <span className="font-mono text-xs text-[#f5f1e8]">On error, try next provider</span>
            </label>
          </Field>
        </div>
        {error && <p className="text-xs font-mono text-[#e8c4c4] bg-[#3a1a1a] p-3 border border-[#6b3a3a]">{error}</p>}
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving}
            className="flex-1 font-mono text-xs uppercase tracking-widest py-3 bg-[#d8a657] text-[#0a0908] hover:bg-[#e8b867] disabled:opacity-50">
            {saving ? 'Saving…' : initial ? 'Save changes' : 'Create rule'}
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
