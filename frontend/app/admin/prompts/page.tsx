'use client';

import { useEffect, useState } from 'react';
import { Card, Input, Textarea, Select, Button, Badge, Modal, Loader, ErrorState } from '@/components/UI';
import { apiCreatePrompt, apiDeletePrompt, apiListPrompts, apiUpdatePrompt } from '@/lib/api';
import type { CustomPrompt, PromptInput } from '@/lib/api';

const EXTREME_DIRECTNESS = 'extreme_directness';
const UNCENSORED_EXTREME = 'uncensored_extreme';
const PRESET_PROMPTS = new Set<string>([EXTREME_DIRECTNESS, UNCENSORED_EXTREME]);
const PRESET_LABELS: Record<string, string> = {
  custom: 'Custom',
  [EXTREME_DIRECTNESS]: 'Extreme Directness',
  [UNCENSORED_EXTREME]: 'Uncensored (Extreme)',
};
const emptyForm: PromptInput = {
  name: '',
  model_pattern: '*',
  content: '',
  preset: 'custom',
  is_active: true,
  is_default: false,
};

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<CustomPrompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editor, setEditor] = useState<PromptInput | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setPrompts(await apiListPrompts());
    } catch (e: any) {
      setError(e.message || 'Unable to load prompts');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  function openNew() {
    setEditingId(null);
    setEditor({ ...emptyForm });
    setNotice(null);
  }

  function openEdit(prompt: CustomPrompt) {
    setEditingId(prompt.id);
    setEditor({
      name: prompt.name,
      model_pattern: prompt.model_pattern,
      content: PRESET_PROMPTS.has(prompt.preset) ? '' : prompt.content,
      preset: prompt.preset,
      is_active: prompt.is_active,
      is_default: prompt.is_default,
    });
    setNotice(null);
  }

  async function save() {
    if (!editor) return;
    setSaving(true);
    setNotice(null);
    try {
      if (editingId) await apiUpdatePrompt(editingId, editor);
      else await apiCreatePrompt(editor);
      setEditor(null);
      await load();
      setNotice('Prompt saved.');
    } catch (e: any) {
      setNotice(e.message || 'Unable to save prompt');
    } finally {
      setSaving(false);
    }
  }

  async function remove(prompt: CustomPrompt) {
    if (!window.confirm(`Delete ${prompt.name}?`)) return;
    try {
      await apiDeletePrompt(prompt.id);
      await load();
    } catch (e: any) {
      setNotice(e.message || 'Unable to delete prompt');
    }
  }

  if (loading) return <Loader label="Loading prompts" />;
  if (error) return <ErrorState error={error} onRetry={load} />;

  return (
    <div className="stack">
      <header className="section-head">
        <div>
          <div className="section-eyebrow">Section 05 / Prompts</div>
          <h1 className="section-title">Your model prompts</h1>
          <p className="section-sub mono">Private to this account · {prompts.length}/50 saved</p>
        </div>
        <Button onClick={openNew}>+ Add prompt</Button>
      </header>

      <Card title="Prompt library" eyebrow="server-side behavior">
        <p className="text-sm muted" style={{ marginBottom: '1rem' }}>
          Prompts are applied by the gateway to matching models. They are never shared with other accounts.
        </p>
        {notice && <div className="badge badge-info" style={{ marginBottom: '0.75rem' }}>{notice}</div>}
        {prompts.length === 0 ? (
          <div className="empty-box">No prompts yet. Add one for a model, use <b>Extreme Directness</b> for a concise style, or <b>Uncensored (Extreme)</b> for an unfiltered private style.</div>
        ) : (
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>Name</th><th>Target</th><th>Preset</th><th>State</th><th /></tr></thead>
              <tbody>
                {prompts.map((prompt) => (
                  <tr key={prompt.id}>
                    <td className="text-sm wrap">{prompt.name}{prompt.is_default && <span className="dim text-xs"> · default</span>}</td>
                    <td className="mono text-xs">{prompt.model_pattern}</td>
                    <td><Badge variant={prompt.preset === UNCENSORED_EXTREME ? 'err' : prompt.preset === EXTREME_DIRECTNESS ? 'warn' : 'default'}>{PRESET_LABELS[prompt.preset] || 'Custom'}</Badge></td>
                    <td><Badge variant={prompt.is_active ? 'ok' : 'mute'}>{prompt.is_active ? 'Active' : 'Off'}</Badge></td>
                    <td><div className="row" style={{ justifyContent: 'flex-end' }}><Button size="sm" variant="ghost" onClick={() => openEdit(prompt)}>Edit</Button><Button size="sm" variant="danger" onClick={() => remove(prompt)}>Delete</Button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {editor && (
        <Modal open title={editingId ? 'Edit prompt' : 'Add prompt'} onClose={() => setEditor(null)} width="lg" footer={<div className="row" style={{ justifyContent: 'flex-end' }}><Button variant="ghost" onClick={() => setEditor(null)}>Cancel</Button><Button onClick={save} disabled={saving || !editor.name.trim() || (!PRESET_PROMPTS.has(editor.preset) && !editor.content.trim())}>{saving ? 'Saving…' : 'Save prompt'}</Button></div>}>
          <div className="stack">
            <Input label="Name" value={editor.name} onChange={(v) => setEditor({ ...editor, name: v })} placeholder="e.g. API architect" maxLength={80} />
            <Input label="Model target" value={editor.model_pattern} onChange={(v) => setEditor({ ...editor, model_pattern: v })} hint="Use an exact model ID or a trailing wildcard such as gpt-4o*." maxLength={255} />
            <Select label="Preset" value={editor.preset} onChange={(v) => setEditor({ ...editor, preset: v as PromptInput['preset'] })} options={[{ value: 'custom', label: 'Custom prompt' }, { value: EXTREME_DIRECTNESS, label: 'Extreme Directness' }, { value: UNCENSORED_EXTREME, label: 'Uncensored (Extreme)' }]} hint="Extreme Directness trims filler. Uncensored (Extreme) removes refusals and safety commentary for private use — provider limits and hard illegal-content rules still apply." />
            {!PRESET_PROMPTS.has(editor.preset) && <Textarea label="Prompt" value={editor.content} onChange={(v) => setEditor({ ...editor, content: v })} rows={10} placeholder="Describe how the model should respond…" hint="Maximum 12,000 characters." />}
            <label className="row" style={{ gap: '0.5rem', cursor: 'pointer' }}><input type="checkbox" checked={editor.is_default} onChange={(e) => setEditor({ ...editor, is_default: e.target.checked })} /><span className="text-sm">Use as this account's default prompt for matching models</span></label>
            <label className="row" style={{ gap: '0.5rem', cursor: 'pointer' }}><input type="checkbox" checked={editor.is_active} onChange={(e) => setEditor({ ...editor, is_active: e.target.checked })} /><span className="text-sm">Active</span></label>
          </div>
        </Modal>
      )}
    </div>
  );
}
