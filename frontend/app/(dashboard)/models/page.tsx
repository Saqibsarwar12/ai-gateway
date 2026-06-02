'use client';

import { useEffect, useState } from 'react';
import { Card, ErrorState, Loader, Modal } from '@/components/UI';
import { api, type AIModel, type Provider } from '@/lib/api';

export default function ModelsPage() {
  const [models, setModels] = useState<AIModel[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<AIModel | null>(null);
  const [showNew, setShowNew] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([api.listModels(), api.listProviders()])
      .then(([m, p]) => { setModels(m); setProviders(p); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this model?')) return;
    await api.deleteModel(id).catch(() => {});
    load();
  };

  if (loading) return <Loader label="Loading models" />;
  if (error) return <ErrorState error={error} />;

  return (
    <div className="space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <p className="font-mono text-[10px] tracking-[0.4em] text-[#6b6358] uppercase mb-2">Section 03 / Catalog</p>
          <h1 className="font-serif text-5xl italic">Model catalog</h1>
          <p className="mt-3 text-sm text-[#8a8278] font-mono">{models.length} models · discovered from {providers.length} providers</p>
        </div>
        <button onClick={() => setShowNew(true)}
          className="font-mono text-xs uppercase tracking-widest px-6 py-3 bg-[#d8a657] text-[#0a0908] hover:bg-[#e8b867]">
          + Add model
        </button>
      </header>

      {models.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="font-serif italic text-2xl text-[#8a8278] mb-2">No models yet</p>
            <p className="font-mono text-xs text-[#6b6358] mb-6">Add a provider first, then sync or manually add models.</p>
            <button onClick={async () => {
              for (const p of providers) await api.syncProviderModels(p.id).catch(() => {});
              load();
            }} className="font-mono text-xs uppercase tracking-widest px-4 py-2 border border-[#d8a657] text-[#d8a657] hover:bg-[#d8a657] hover:text-[#0a0908]">
              Sync from providers
            </button>
          </div>
        </Card>
      ) : (
        <div className="border-t border-[#3a342c]">
          {models.map((m) => {
            const provider = providers.find((p) => p.id === m.provider_id);
            return (
              <div key={m.id} className="grid grid-cols-12 gap-3 py-4 border-b border-[#2a2520] hover:bg-[#1a1612]">
                <div className="col-span-4 px-2">
                  <p className="font-serif text-lg text-[#f5f1e8]">{m.name}</p>
                  <p className="font-mono text-[10px] text-[#6b6358] mt-0.5">{m.model_id}</p>
                </div>
                <div className="col-span-2 px-2 font-mono text-xs text-[#8a8278] self-center">{provider?.name || m.provider_id || '—'}</div>
                <div className="col-span-1 px-2 font-mono text-xs text-[#d8a657] self-center text-right">${m.input_cost_per_1m.toFixed(2)}/M</div>
                <div className="col-span-1 px-2 font-mono text-xs text-[#d8a657] self-center text-right">${m.output_cost_per_1m.toFixed(2)}/M</div>
                <div className="col-span-1 px-2 font-mono text-xs text-[#8a8278] self-center text-right">{m.context_window.toLocaleString()}</div>
                <div className="col-span-1 px-2 self-center text-right">
                  <span className={`font-mono text-[10px] px-2 py-0.5 ${m.is_active ? 'bg-[#4a6b3a] text-[#d4e8c4]' : 'bg-[#3a342c] text-[#8a8278]'}`}>
                    {m.is_active ? 'ON' : 'OFF'}
                  </span>
                </div>
                <div className="col-span-2 px-2 self-center text-right space-x-1">
                  <button onClick={() => setEditing(m)}
                    className="font-mono text-[10px] uppercase tracking-widest px-2 py-1 border border-[#3a342c] text-[#f5f1e8] hover:border-[#d8a657]">
                    Edit
                  </button>
                  <button onClick={() => handleDelete(m.id)}
                    className="font-mono text-[10px] uppercase tracking-widest px-2 py-1 border border-[#6b3a3a] text-[#e8c4c4] hover:bg-[#6b3a3a] hover:text-[#0a0908]">
                    ×
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {(showNew || editing) && (
        <ModelForm initial={editing} providers={providers}
          onClose={() => { setShowNew(false); setEditing(null); }}
          onSaved={() => { setShowNew(false); setEditing(null); load(); }} />
      )}
    </div>
  );
}

function ModelForm({ initial, providers, onClose, onSaved }: { initial: AIModel | null; providers: Provider[]; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(initial?.name || '');
  const [modelId, setModelId] = useState(initial?.model_id || '');
  const [providerId, setProviderId] = useState(initial?.provider_id || '');
  const [inputCost, setInputCost] = useState(initial?.input_cost_per_1m || 0);
  const [outputCost, setOutputCost] = useState(initial?.output_cost_per_1m || 0);
  const [context, setContext] = useState(initial?.context_window || 8192);
  const [isActive, setIsActive] = useState(initial?.is_active !== false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const data = {
        name,
        model_id: modelId,
        provider_id: providerId,
        input_cost_per_1m: inputCost,
        output_cost_per_1m: outputCost,
        context_window: context,
        is_active: isActive,
      };
      if (initial) {
        await api.updateModel(initial.id, data);
      } else {
        await api.createModel(data);
      }
      onSaved();
    } catch (e: any) {
      setError(e.message);
    }
    setSaving(false);
  };

  return (
    <Modal open title={initial ? 'Edit model' : 'Add model'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Display name">
            <input value={name} onChange={(e: any) => setName(e.target.value)} required
              className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
          </Field>
          <Field label="Model ID">
            <input value={modelId} onChange={(e: any) => setModelId(e.target.value)} required placeholder="gpt-4o-mini"
              className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
          </Field>
        </div>
        <Field label="Provider">
          <select value={providerId} onChange={(e) => setProviderId(e.target.value)} required
            className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none">
            <option value="">Select a provider</option>
            {providers.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="$/M input">
            <input type="number" step="0.01" value={inputCost} onChange={(e) => setInputCost(Number(e.target.value))}
              className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
          </Field>
          <Field label="$/M output">
            <input type="number" step="0.01" value={outputCost} onChange={(e) => setOutputCost(Number(e.target.value))}
              className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
          </Field>
          <Field label="Context">
            <input type="number" value={context} onChange={(e) => setContext(Number(e.target.value))}
              className="w-full bg-[#0a0908] border border-[#3a342c] px-3 py-2 text-sm font-mono text-[#f5f1e8] focus:border-[#d8a657] outline-none" />
          </Field>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="accent-[#d8a657]" />
          <span className="font-mono text-xs text-[#f5f1e8]">Active and routable</span>
        </label>
        {error && <p className="text-xs font-mono text-[#e8c4c4] bg-[#3a1a1a] p-3 border border-[#6b3a3a]">{error}</p>}
        <div className="flex gap-3 pt-2">
          <button type="submit" disabled={saving}
            className="flex-1 font-mono text-xs uppercase tracking-widest py-3 bg-[#d8a657] text-[#0a0908] hover:bg-[#e8b867] disabled:opacity-50">
            {saving ? 'Saving…' : initial ? 'Save' : 'Create'}
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
